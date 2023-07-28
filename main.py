import sys
from monitoring_classes import *

monitorings_df = get_dataframe_fromBQ(MONITORINGS_SETTINGS_FULL_TABLE_NAME)
monitors_df = get_dataframe_fromBQ(MONITORS_FULL_TABLE_NAME)
snapshots = get_dataframe_fromBQ(SNAPSHOTS_FULL_TABLE_NAME)

if monitors_df.empty or monitors_df.empty or snapshots.empty:
    print("One of the monitoring tables is empty, check either connection to database or its tables")
    sys.exit()

for index, row in monitorings_df.iterrows():
    monitoring = MonitoringSettings(row)
    old_table, new_table = None, None
    try:
        new_table = TableSnapshot(snapshot=get_filtered_table(monitoring.full_table_name, monitoring.controls),
                                  monitoring_id=monitoring.id)
        snapshot_df = pd.read_json(snapshots.loc[snapshots['monitoring_id'] == monitoring.id, 'snapshot'].iloc[0], dtype='str')
        old_table = TableSnapshot(snapshot=snapshot_df, monitoring_id=monitoring.id)
    except (ValueError, AttributeError, IndexError):
        print("No snapshots were found for the registered monitoring yet. The first snapshot will be saved to table.")
        if old_table is None:
            new_table.first_time_save_to_bq()
            monitoring.save_monitors_to_bq()
            continue
    except Exception as e:
        print(f"An exception of type {type(e).__name__} occurred: {e}")
        continue

    monitoring.monitors = monitors_df.loc[monitors_df['monitoring_id'] == monitoring.id, 'monitor'].to_list()
    email_builder = EmailBuilder(monitoring)

    if bool(set(old_table.snapshot.columns) ^ set(new_table.snapshot.columns)):
        new_table.first_time_save_to_bq()
        continue

    if monitoring.controls_option == "keys":
        missing_keys, modified_keys = None, None
        target_column = monitoring.controls[0].name  # there is only 1 column for control when controls_option == "keys"

        if "missing_keys" in monitoring.monitored_changes:
            missing_keys = get_missing_keys(monitoring.controls, new_table.snapshot)
            if missing_keys:
                if monitoring.key_removal_action == "remove":
                    monitoring.remove_missing_keys(missing_keys)  # controls in new_table are already gone
                    monitoring.update_self_to_database()
                email_builder.add_to_body("missing_keys", missing_keys)

        if "modified_keys" in monitoring.monitored_changes:
            missing_rows = get_missing_rows(old_table.snapshot, new_table.snapshot)
            modified_keys = get_modified_keys(missing_rows.to_dict("records"),
                                                      new_table.snapshot.to_dict("records"),
                                                      monitoring.conditions)
            if modified_keys:
                if monitoring.condition_change_action == "remove":
                    keys_to_remove = [row["older_row"][target_column] for row in modified_keys]
                    monitoring.remove_missing_keys(keys_to_remove)
                    monitoring.update_self_to_database()
                new_table.remove_modified_keys(modified_keys, target_column)
                email_builder.add_to_body("modified_keys", modified_keys)

        if missing_keys or modified_keys:
            new_table.update_self_to_bq()

    elif monitoring.controls_option == "filters":
        new_conditions, missing_conditions = pd.DataFrame, pd.DataFrame
        controls = [c.name for c in monitoring.controls]
        conditions = monitoring.conditions

        if "missing_condition" in monitoring.monitored_changes:
            missing_conditions = get_modified_conditions(conditions, controls + conditions,
                                                         old_table.snapshot, new_table.snapshot)
        if "new_condition" in monitoring.monitored_changes:
            new_conditions = get_modified_conditions(conditions, controls + conditions,
                                                     new_table.snapshot, old_table.snapshot)

        if not missing_conditions.empty:
            email_builder.add_to_body("missing_conditions", missing_conditions.to_dict("records"))
            look_for_conditions = [record[monitoring.conditions[0]] for record in missing_conditions.to_dict("records")]
            replacement_conditions = get_table_from_values_in_column(monitoring.full_table_name,
                                                                     monitoring.conditions[0],
                                                                     look_for_conditions)
            if not replacement_conditions.empty:
                email_builder.add_to_body("conditions_replacements", replacement_conditions.to_dict("records"))
        if not new_conditions.empty:
            email_builder.add_to_body("new_conditions", new_conditions.to_dict("records"))
        if not new_conditions.empty or not missing_conditions.empty:
            new_table.update_self_to_bq()

    if email_builder.changes_found:
        # with open("check_email_body.html", "w", encoding='UTF-8') as f:  # TODO: NO NEED TO KEEP
        #     f.write(email_builder.email_body)
        email_builder.send_email_to_monitors()