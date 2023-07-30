# A monitoring alert tool ⚠️
A tool to generate alerts over user-defined modifications in monitored tables

**So far, only BIG QUERY tables have been set up for monitoring**


## What can this monitoring tool do?
It may identify specific modifications on “monitored controls”(columns) of a table, either by “keys” (values of a column, such as specific emails in an "email" column) or filters on tables, to send monitors alert emails about relevant the relevant found changes.

Relevant alterations are set for the table columns in the settings of a monitoring as “conditions”, which are data in other columns related to the control, which variation interests a monitor.

Albeit it can monitor any table, it is recommended to be used upon data marts updated by overwriting, not appending.

EMAIL EXAMPLE
![image](https://github.com/cgodevs/monitoring-alert-tool/assets/69640514/ef22688b-ad31-43ce-9f03-83b2dd7c40f0)


## What questions may be answered?
Examples:
- Given a set of monitored people, did any of them change their job position, project, or community? What was your allocation like before and how is it now? Application examples:
  - Control over allocation changes for Trainees: Removing basic accesses and looking forward to renew them with leaders
  - Control over allocation changes for people with access to a Data product: remove access to the product and understand whether it is now possible to   delete it
  - Participation list control in meetings whose participants do not follow the same criteria and people who may not be simply filtered in updated spreadsheets.
- Has a new manager, intern, developer or whatever skill employee been admitted to community X or project Y? Has any of the previous people in these positions left?
- Has a member of my team registered a new day-off?
- Has a member of my team registered a new trip?


## How does it work?
#### OVERVIEW
The script reads monitoring settings stored in a Big Query table, generates and also stores a JSON snapshot in Big Query for the current state of a monitoring table, filtered according to the controls indicated in the monitoring settings.
In the next executions, it performs constant comparisons between the stored snapshot and the updated and filtered table again, to look for differences between both and alert them to the monitor(s), if they are configured as relevant to generate an alert (being “conditions ”).
Note: Here we take advantage of Big Query's non-relational character to store semi-structured data (JSONs)

There are 2 types of monitoring:
- Key control, for when you know exactly who or what you want to monitor or
- Filter control, for when there is no one or what to specifically monitor, however you want to know inputs or outputs of a specific data following common patterns, which are the filters.


#### DETAILS
A service account, with read access to the tables that can be monitored and written to the monitoring dataset, is used to connect to Big Query and another account (with proper sending permission) to send alert emails. Credentials for accessing both accounts are extracted from the AWS Secret Manager service.
Ideally, it should operate on a daily basis, configured in a flow orchestration tool (DAG in Airflow).
After storing the monitoring in its table in BQ, the first execution of the script feeds the snapshot table with the first snapshot derived from the filtered table (indicated in the monitoring settings) (according to the monitoring configuration as well) and the monitors table with the monitors registered in the settings. From the second run, the script must already perform data verification between the saved snapshot and a new version of the filtered table that initially originated it.

All data is received from the monitored table as string, being saved in the JSON of the snapshot as strings as well.
A python script can be run locally by a person with the proper access:
- To  AWS SecretManager Service in an AWS Account
- AWS SSO login to the analytics account on your local machine

## Example of Monitoring
**Title:**
Monitoring on position or project changes for interns

**Description:**
Remove access from tools X, Y and Z

**Monitor:**
my.account@mail.com

**Monitoring Control Type** (would you like to monitor specific criteria?):
Yes, I will set up my monitoring according to “keys” (unique corporate email)

**What changed conditions should be alerted to?**
Job Position or Project

**Table of monitored controls:**
my-project.allocation.current_allocation_table

**Changes in view per alert:**
Controls with modified conditions (position, project…) or deleted controls

**What are the controls (people) monitored?**
intern1@mail.com, intern2@mail.com

**Want to view other data related to controls in the report email?**
Business name and primary leader email address

**Keep the controls on the watchlist in case they change?**
No

**Keep controls in watchlist in case they are deleted?**
No


## Transcription of the above example into semi-structured data (JSON)
```
{
     "monitoring_title": "Monitoring on position or project changes for interns",
     "monitoring_description": "Removeng access from tools X, Y and Z",
     "monitors": ["my.account@mail.com"],
     "controls_option": "keys",
     "full_table_name": "my-project.allocation.current_allocation_table",
     "monitored_changes": ["modified_keys", "missing_keys"],
     "controls": [
         {
             "control_link": "equals",
             "control_name": "ds_email",
             "control_values": ["intern1@mail.com", "intern2@mail.com"]
         }
     ],
     "conditions": [
         "project",
         "job_position"
     ],
     “other_reported_conditions”: [“department”, “primary_leader_address”],
     "condition_change_action": "remove",
     "key_removal_action": "remove"
}
```


## How to build the monitoring JSON?
Be careful about including every single one of the parameters indicated below, also in watch out for syntax and the data type expected as a value.

**`monitoring_title`**(string): The monitoring title, appears in the email title. Be sure to choose a name that is clear enough to remind you of the purpose of the monitoring.

**`monitoring_description`**(string): Monitoring description. You can take the opportunity to increase the activities that you need to remember to perform, in case any changes are identified.

**`monitors`**(list): The initial email recipients of people who should be alerted. The set of these emails is only used initially to define the monitors. Subsequently, the set of monitors is defined by the table that stored them after the first execution of the script for the newly created monitoring.

**`full_table_name`**(string): The full name of the monitored table. It will be used in the query that will filter the target table according to the controls indicated in the configuration. In GCP BQ follows the pattern: project_name.dataset_name.table_name (eg: zup-intelligence.dm_corporate_data.mvw_current_allocation)

**`controls_option`**(string): Definition of the monitoring type. Must be one of the values “keys” or “filters”. Important for directing the comparison logic. “keys” refers to the type that considers only one column as a control, and always checks whether the conditions of the other columns of interest have changed. “filters” is the type that will always filter the target table according to the set of defined controls (like in a common spreadsheet or table filtering) and check if one of the saved values of the single column defined as “condition” was not found (control removed) or if a new control appeared (new control).
“keys” and “filters” operate in different ways to interpret the configurations of “controls” and “conditions”. It is important to choose the correct option!

**`other_reported_conditions`**(list): The names of other columns related to the controls you would also like to see data about in the report email


### KEY MONITORING CASE (keys)
For when you know exactly who or what you want to monitor.
The concept of "control" is interpreted by this type of monitoring as a single column in the monitored table, for which monitoring is performed on exact values ("keys") contained therein.

**`monitored_changes`**(list): Which type of changes should be notified. Only accepts the values: "missing_keys" and/or "modified_keys"
- missing_keys: the alert will point out the absence of a key in the control column
- modified_keys: the alert will point out modifications in one or more data related to a monitored key, located in the other columns indicated as "conditions" (see below)
If changes are identified in the monitored keys, a new version of the monitored and filtered table will always be saved.

**`controls`**(list of dictionaries): Must contain only 1 dictionary for this type of monitoring
- **`control_name`**(string): Name of the column containing the keys
- **`control_link`**(string): Must be equal to "equals" for this type of monitoring. Indicates how the above controls should be queried on the column. The value "equals" requires exact match between searched and monitored values.
- **`control_values`**(list): The list of exact monitored keys found only in the control column of the monitored table

**`conditions`**(list): Other columns of the monitored table, other than the controls column. A modification to one of these columns indicates that the control has been modified and an alert should be sent.

**`key_removal_action`**(string): the value “remove” indicates that keys not found must be removed from the list of monitored keys, in the monitoring settings. Any other value has no function.adade.

**`condition_change_action`**(string): the value “remove” indicates that keys not found must be removed from the list of monitored keys, in the monitoring settings. Any other value has no functionality.


### FILTERS MONITORING CASE (filters)
For when there is no one or what to monitor specifically, however you want to know inputs or outputs of a specific data according to common patterns, which are the filters.
The concept of "controls" is interpreted by this type of monitoring as the set of columns that the monitor wants to filter, to monitor changes in other columns indicated as "conditions". The control interpretation here is different from the previous monitoring.

**`monitored_changes`**(list): Allows the values “missing_condition” or “new_condition”.
- missing_condition: the alert will point out the absence of a key in the conditions column
- new_condition: the alert will point out changes in one or more data related to a monitored key, located in the other columns indicated as "conditions" (see below)

**`controls`**(list of dictionaries): These are the columns that will be filtered. Each dictionary indicates a different column.
- **`control_name`**(string): Name of the column that will be filtered
- **`control_link`** (string): It can be equal to "equals" or "contains" and indicates how the columns will be filtered. The value "equals" indicates that there must be an exact match with one or more values in the control_values list for it to be filtered. The value “contains” indicates that a correspondence between the values of the filtered column and those contained in the control_values list is sufficient for the record to be admitted to the filtered table.
- **`control_values`**(list): The list of exact monitored keys found only in the control column of the monitored table

**`conditions`**(list): It must be a list with only one item (string), this item is the name of the column that will be used to differentiate the entry of new values in the filtered table or output of values stored in the old snapshot.

**`condition_change_action`**(string): Does not have functionality in this type of monitoring. It accepts any value.

**`key_removal_action`**(string): Does not have functionality in this type of monitoring. It accepts any value.


## Saving the monitoring JSON to database 
Because there is no API yet, you must build a query. If you choose to insert directly, open a new tab in the GCP BQ console and type:

INSERT INTO \`my-project.allocation.current_allocation_table\` (id, creation_date, settings)
VALUES ((SELECT MAX(id) + 1 FROM \`my-project.allocation.current_allocation_table\`), CURRENT_TIMESTAMP(), JSON '{"monitoring_title": "Monitoring on position or project changes for interns","monitoring_description": "Removeng access from tools X, Y and Z","monitors": ["my.account@mail.com"],"controls_option": "keys","full_table_name": "my-project.allocation.current_allocation_table","monitored_changes": ["modified_keys", "missing_keys"],"controls": [{"control_link": "equals","control_name": "ds_email","control_values": ["intern1@mail.com", "intern2@mail.com"]}],"conditions": ["project","job_position"],"other_reported_conditions": ["department", "primary_leader_address"],"condition_change_action": "remove","key_removal_action": "remove"}');

Replace the JSON template with the one you've created and run the command.


