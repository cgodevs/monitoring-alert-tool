import json
import boto3
import pandas as pd
import subprocess
from google.cloud import bigquery
from google.oauth2 import service_account


def sso_login():
    subprocess.run(['aws', 'sso', 'login'], check=True)


def get_aws_secret(secret_name):
    session = boto3.Session()
    client = session.client(service_name='secretsmanager', region_name=REGION_NAME)
    response = client.get_secret_value(SecretId=secret_name)
    secret = response.get('SecretString', response.get('SecretBinary'))
    return json.loads(secret)


def get_connection_to_bq():
    secret = get_aws_secret(secret_name=AWS_SERVICE_ACCOUNT_SECRET_NAME)
    gbq_credentials = service_account.Credentials.from_service_account_info(secret)
    return bigquery.Client(credentials=gbq_credentials)


# ----------------------------------------------------------------------------------------------------
# -------------------------------------- BIG QUERY DATABASE MANIPULATION ---------------------------------------
# ----------------------------------------------------------------------------------------------------


def get_filtered_table(full_table_name, controls: list):
    query = f"SELECT * FROM {full_table_name} WHERE TRUE "
    for control in controls:
        if control.link == "contains":
            substring_values_list = [f"'%{value.strip()}%'" for value in control.values]
            joined_conditions = " OR ".join([f"{control.name} LIKE {value}" for value in substring_values_list])
            query += f"AND ({joined_conditions}) "
        if control.link == "equals":
            values_list = ", ".join([f"'{value.strip()}'" for value in control.values for control in controls])
            query += f"AND {control.name} IN ({values_list}) "
    query_job = send_query_to_bq(query)
    if query_job is None:
        return pd.DataFrame()
    filtered_database = query_job.to_dataframe().astype(str)
    return filtered_database


def get_table_from_values_in_column(table_name, column: str, values: list):
    set_of_values = ", ".join([f"'{value}'" for value in values])
    query = f"SELECT * FROM {table_name} WHERE {column} IN ({set_of_values}) "
    query_job = send_query_to_bq(query)
    if query_job is None:
        return pd.DataFrame()
    return query_job.to_dataframe().astype(str)


def get_dataframe_fromBQ(full_table_name):
    try:
        table = BQ_CLIENT.get_table(full_table_name)
        df = BQ_CLIENT.list_rows(table).to_dataframe()
    except ValueError:
        print("No data found in table " + full_table_name)
        return pd.DataFrame()
    except Exception as e:
        print(f"An exception of type {type(e).__name__} occurred: {e}")
        return pd.DataFrame()
    return df


def send_query_to_bq(query, msg=None):
    try:
        query_job = BQ_CLIENT.query(query)
        results = query_job.result()
        if results.total_rows == 0:
            return None
        if msg is not None:
            print(msg)
        return query_job
    except Exception as e:
        print(f"An exception of type {type(e).__name__} occurred: {e}")
        return None
# -------------------------------------------------------------------
# ----------------------- VERIFICATION FUNCTIONS --------------------
# -------------------------------------------------------------------

def get_missing_keys(controls: list, new_snapshot: pd.DataFrame):
    target_column, link, monitored_keys = controls[0].name, controls[0].link, controls[0].values
    keys_in_new_table = new_snapshot[target_column].drop_duplicates().to_list()
    missing_keys = None
    if link == "equals":
        missing_keys = [key for key in monitored_keys if key not in keys_in_new_table]
    elif link == "contains":
        missing_keys = [key for key in monitored_keys if
                            not any(key in value for value in keys_in_new_table)]
    return missing_keys


def get_missing_rows(old_snapshot: pd.DataFrame, new_filtered_table: pd.DataFrame):
    merged = old_snapshot.merge(new_filtered_table, indicator=True, how='outer')
    missing_rows = merged[merged['_merge'] == 'left_only']
    missing_rows = missing_rows.drop(columns=['_merge'])
    return missing_rows


def equals_all_but_conditions(this_row, other_row, conditions):
    other_attributes = [attr for attr in this_row if attr not in conditions]
    for attr in other_attributes:
        if this_row[attr] != other_row[attr]:
            return False
    for condition in conditions:
        if this_row[condition] != other_row[condition]:
            return True
    return False


def get_modified_keys(missing_monitored_rows: list, filtered_database: list, conditions: list):
    modified_keys = []
    for missing_row in missing_monitored_rows:
        for filtered_row in filtered_database:
            if equals_all_but_conditions(missing_row, filtered_row, conditions):
                change_info = {
                    "older_row": missing_row,
                    "newer_row": filtered_row,
                    "previous_state_conditions": {
                                                    condition: missing_row[condition] for condition in conditions
                                                    if missing_row[condition] != filtered_row[condition]
                                                },
                    "current_state_conditions": {
                                                    condition: filtered_row[condition] for condition in conditions
                                                    if missing_row[condition] != filtered_row[condition]
                                                }
                }
                modified_keys.append(change_info)
    return modified_keys



def get_modified_conditions(conditions, target_columns, old_snapshot: pd.DataFrame, new_filtered_table: pd.DataFrame):
    missing_conditions = pd.DataFrame(columns=old_snapshot.columns)  # Create empty dataframe to store missing rows
    for index, row in old_snapshot.iterrows():
        snapshot_conditions = row[target_columns]  # Get the values in the conditions columns for the current row
        matching_row = new_filtered_table[(new_filtered_table[target_columns] == snapshot_conditions).all(axis=1)]
        if matching_row.empty:
            missing_conditions = missing_conditions.append(row, ignore_index=True)
    conditions_match = missing_conditions[conditions]\
                        .apply(tuple, axis=1)\
                        .isin(new_filtered_table[conditions].apply(tuple, axis=1))
    missing_conditions = missing_conditions[~conditions_match]
    return missing_conditions


REGION_NAME = ""
AWS_SERVICE_ACCOUNT_SECRET_NAME = ""
AWS_MAILER_ACCOUNT_SECRET_NAME = ""
SECRET_USERNAME_KEY = ""
SECRET_PASSWORD_KEY = ""
MONITORINGS_SETTINGS_FULL_TABLE_NAME = ""
MONITORS_FULL_TABLE_NAME = ""
SNAPSHOTS_FULL_TABLE_NAME = ""

# sso_login()
MAILER_ACCOUNT_SECRET = get_aws_secret(secret_name=AWS_MAILER_ACCOUNT_SECRET_NAME)
BQ_CLIENT = get_connection_to_bq()
