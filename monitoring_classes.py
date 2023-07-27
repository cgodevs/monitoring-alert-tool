from monitoring_utils import *
from email_snippets_variables import snippets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import googleapiclient.discovery
from botocore.exceptions import ClientError
from datetime import datetime
import pandas_gbq


class MonitoringSettings:
    def __init__(self, df_row):
        self.id = df_row['id']
        self.json_settings = json.loads(df_row['settings'])
        self.__dict__.update(self.json_settings)
        self.controls = [Control(control) for control in self.json_settings["controls"]]

    def remove_missing_controls(self, missing_controls):
        monitored_control_values = [value for value in self.json_settings["controls"][0]["control_values"]
                                    if value not in missing_controls]
        self.json_settings["controls"][0]["control_values"] = monitored_control_values

    def update_self_to_database(self):
        json_string = json.dumps(self.json_settings, indent=4, ensure_ascii=False)
        json_string = re.sub(r'\s{4,}', '', json_string).replace('\n', '')
        query = f"UPDATE `{MONITORINGS_SETTINGS_FULL_TABLE_NAME}` " \
                f"SET settings = JSON '{json_string}' " \
                f"WHERE id = {self.id}"
        send_query_to_bq(query, f"monitoring_id = {self.id} settings's been updated to BQ")

    def save_monitors_to_bq(self):
        for monitor in self.monitors:
            query = f"INSERT INTO `{MONITORS_FULL_TABLE_NAME}` (monitoring_id, monitor) " \
                    f"VALUES ({self.id}, '{monitor}')"
            send_query_to_bq(query, f"monitoring_id = {self.id} settings's been saved to BQ")


class TableSnapshot:
    def __init__(self, snapshot: pd.DataFrame = None, monitoring_id=None):
        self.monitoring_id = monitoring_id
        self.snapshot = snapshot.astype(str)
        self.snapshot_dicts = json.loads(self.snapshot \
                                         .to_json(orient='records', date_format='iso', force_ascii=False) \
                                         .replace('T00:00:00.000Z', '').replace('\\', ''))

    def get_json_string(self):
        json_string = json.dumps(self.snapshot_dicts, indent=4, ensure_ascii=False)
        json_string = re.sub(r'\s{4,}', '', json_string).replace('\n', '').replace("'", "\\'")
        return json_string

    def update_self_to_bq(self):  # json_dumps serves the purpose of adding double quotes in the json string
        query = f"UPDATE `{SNAPSHOTS_FULL_TABLE_NAME}` " \
                f"SET snapshot = JSON '{self.get_json_string()}', " \
                f"last_update = CURRENT_TIMESTAMP(), " \
                f"number_of_updates = number_of_updates + 1 " \
                f"WHERE monitoring_id = {self.monitoring_id}"
        send_query_to_bq(query, f"monitoring_id = {self.monitoring_id} snapshot's been updated to BQ ")

    def first_time_save_to_bq(self):
        query = f"INSERT INTO `{SNAPSHOTS_FULL_TABLE_NAME}` " \
                f"(monitoring_id, last_update, number_of_updates, snapshot) " \
                f"VALUES ({self.monitoring_id}, CURRENT_TIMESTAMP(), 0, JSON '{self.get_json_string()}')"
        send_query_to_bq(query, f"monitoring_id = {self.monitoring_id} snapshot's been saved to BQ")

    def remove_changed_controls(self, changed_rows, control_name):
        self.snapshot_dicts = [row for row in self.snapshot_dicts
                               for change in changed_rows
                               if row[control_name] != change["newer_row"][control_name]]

    def remove_missing_conditions(self, missing_conditions: pd.DataFrame):
        conditions_to_remove = [tuple(d.items()) for d in missing_conditions.to_dict(orient='records')]
        self.snapshot_dicts = [d for d in self.snapshot_dicts if tuple(d.items()) not in conditions_to_remove]


class Control:
    def __init__(self, control_properties: dict):
        self.name = control_properties["control_name"]
        self.link = control_properties["control_link"]
        self.values = control_properties["control_values"]


class EmailBuilder:
    def __init__(self, monitoring: MonitoringSettings):
        self.changes_found = False
        self.monitoring = monitoring
        self.send_to = monitoring.monitors
        self.email_title = snippets["TITLE"] + monitoring.monitoring_title
        self.email_body = snippets["EMAIL_BODY"] \
            .replace("<!--MONITORING_TITLE-->", self.monitoring.monitoring_title) \
            .replace("<!--MONITORING_DESCRIPTION-->", self.monitoring.monitoring_description) \
            .replace("<!--CONTROL-->", ", ".join([c.name for c in self.monitoring.controls])) \
            .replace("<!--MONITORING_TYPE-->", snippets["CONTROL_PT_TRANSLATION"]
                     .get(self.monitoring.controls_option, "undefined"))

    def insert(self, placeholder, content):
        self.email_body = self.email_body.replace(placeholder, content)

    def add_to_body(self, change_type, changes):
        self.changes_found = True
        if self.monitoring.controls_option == 'keys':
            match change_type:
                case "missing_controls":
                    all_missing_controls_li = '\n'.join(['<li>control</li>'.replace('control', c) for c in changes])
                    self.insert("<!--MISSING_CONTROL-->", snippets["MISSING_CONTROLS_HTML"])
                    self.insert("LIST_ITEM", all_missing_controls_li)
                    if self.monitoring.control_removal_action == "remove":
                        self.insert('<!--CONTROLS_WERE_REMOVED-->', snippets["CONTROLS_WERE_REMOVED_FROM_MONITORING"])

                case "modified_controls":
                    control_name = self.monitoring.controls[0].name
                    modified_controls_list = []
                    for change in changes:
                        modified_control_li = change['older_row'][control_name]
                        modified_conditions = list(change['current_state_conditions'].keys())
                        columns = [col for col in change['older_row'].keys() if col in self.monitoring.conditions] + \
                                  [control_name] + self.monitoring.other_reported_conditions
                        headers = '\n'.join(
                            [f'<th class="{"tg-uzvj" if column in modified_conditions else "tg-9wq8"}">{column}</th>'
                             for column in columns])
                        previous_records = '\n'.join([f'<td class="tg-za14">{change["older_row"][column]}</td>'
                                                      for column in columns])
                        current_records = '\n'.join([
                            f'<td class="{"tg-u7ol" if column in modified_conditions else "tg-za14"}">'
                            f'{change["newer_row"][column]}</td>' for column in columns])

                        comparison_table = snippets["COMPARISON_TABLE"] \
                            .replace('<!--TABLE_HEADERS-->', headers) \
                            .replace('<!--PREVIOUS_RECORD_TDS-->', previous_records) \
                            .replace('<!--CURRENT_RECORD_TDS-->', current_records)  # TODO UNINDENT?

                        info = snippets["MODIFIED_CONTROLS_LIST"] \
                            .replace('<!--CONTROL-->', modified_control_li) \
                            .replace('<!--CONTROL_MODIFICATION-->', ', '.join(modified_conditions)) \
                            .replace('<!--COMPARISON_TABLE-->', comparison_table)
                        modified_controls_list.append(info)

                    self.insert("<!--MODIFIED_CONTROLS-->", snippets["HTML_UL"])
                    self.insert("<!--MODIFIED_CONTROLS_LIST-->", '\n'.join(modified_controls_list))

                    if self.monitoring.condition_change_action == "remove":
                        self.insert("<!--CONTROLS_WERE_MODIFIED-->", snippets["REMOVED_MODIFIED_CONDITIONS_CONTROLS"])

        elif self.monitoring.controls_option == 'filters':
            columns_to_report = self.monitoring.conditions + self.monitoring.other_reported_conditions + \
                                [c.name for c in self.monitoring.controls]
            table = None
            lis = ''
            for control in self.monitoring.controls:
                link_syntax = snippets["LINK_PT_SYNTAX"].get(control.link, 'undefined')
                lis = lis + f"<li> {control.name}: {link_syntax} {', '.join(control.values)}</li>\n"
            ul = '<ul>\n' + lis + '</ul>\n'
            introduction_paragraph = snippets["MODIFIED_CONDITION_PARAGRAPH"] + ul
            self.insert('<!--FILTERS_MONITORING_INTRODUCTION-->', introduction_paragraph)
            headers = '\n'.join(
                [f'<th class="{"tg-uzvj" if column in self.monitoring.conditions else "tg-9wq8"}">{column}</th>'
                 for column in columns_to_report])
            modified_records = ''
            for record in changes:
                modified_records = modified_records + \
                              '<tr>\n' + \
                              '\n'.join([f'<td class="tg-za14">{record[column]}</td>'
                                         for column in columns_to_report]) + \
                              '\n</tr>\n'
            table = snippets["MODIFIED_CONDITIONS_TABLE"] \
                .replace('<!--TABLE_HEADERS-->', headers) \
                .replace('<!--MODIFIED_RECORDS_TRS-->', modified_records)

            match change_type:
                case "new_conditions":
                    new_controls = snippets["NEW_CONDITION_FOUND"]\
                        .replace('<!--NEW_CONTROLS_TABLE-->', table)
                    self.insert('<!--NEW_CONDITIONS-->', new_controls)

                case "missing_conditions":
                    missing_conditions = snippets["MISSING_CONDITION_FOUND"]\
                        .replace('<!--MODIFIED_CONDITIONS_TABLE-->', table)
                    self.insert('<!--MISSING_CONDITIONS-->', missing_conditions)

                case "conditions_replacements":
                    self.insert('<!--MODIFIED_CONDITIONS_NEW_PLACEMENT-->', snippets["CURRENT_CONDITIONS"] + table)
                case _:
                    pass

    def send_email_to_monitors(self):
        username = MAILER_ACCOUNT_SECRET[SECRET_USERNAME_KEY]
        password = MAILER_ACCOUNT_SECRET[SECRET_PASSWORD_KEY]
        from_addr = username

        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = ", ".join(self.send_to)
        msg['Subject'] = self.email_title
        # msg['Bcc'] = ", ".join(hidden)

        msg.attach(MIMEText(self.email_body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.ehlo()
        try:
            server.login(username, password)
            server.sendmail(from_addr, self.send_to, msg.as_string())
        except Exception as e:
            print(f"An exception of type {type(e).__name__} occurred: {e}")
        else:
            print(f"E-mail sent to '{msg['To']}' for monitoring_id = {str(self.monitoring.id)}, "
                  f"description = '{self.monitoring.monitoring_title}'")
        server.quit()
