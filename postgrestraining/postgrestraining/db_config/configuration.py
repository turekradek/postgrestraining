import os.path

# OLD CODE FROM LEGACY VM

from zz_deepscraping_test.deepscraping_utils import deepscraping_views

from os import environ

is_local = environ.get("IS_LOCAL", "").lower() == "true"
user = environ.get("DB_USER", "hosting@az-postgres-ers-prod-01")
password = environ.get("DB_PASSWORD", environ.get("DB_PASSWORD_HOSTING"))
# db
db_host = (
    "localhost"
    if is_local
    else environ.get("DB_SERVER", "az-postgres-ers-prod-01.postgres.database.azure.com")
)
db_host_vm = "localhost" if is_local else "az-postgres-ers-prod-01.postgres.database.azure.com"
db_port = environ.get("DB_PORT", "5432")
db_name = environ.get("DB_NAME", "ers")
db_flags = environ.get("DB_FLAGS", "?sslmode=require")
db_flags = "" if db_flags.lower() == "no_flags" else db_flags

db_url = f"postgresql://{user}:{password}@{db_host}:{db_port}/{db_name}{db_flags}"
db_url_vm = f"postgresql://{user}:{password}@{db_host_vm}:{db_port}/{db_name}{db_flags}"


# databricks
dbr_server_hostname = environ.get("DATABRICKS_SERVER_HOST_NAME")
dbr_http_path = environ.get("DATABRICKS_HTTP_PATH")
dbr_access_token = environ.get("DATABRICKS_ACCESS_TOKEN")

databricks_url = (
    f"databricks://token:{dbr_access_token}@{dbr_server_hostname}?http_path={dbr_http_path}"
)


# search planning
sp_host = environ.get("SEARCH_PLANNING_HOST_NAME")
sp_user = environ.get("SEARCH_PLANNING_USER")
sp_password = environ.get("SEARCH_PLANNING_PASSWORD")
search_planning_url = (
    f"postgresql://{sp_user}:{sp_password}@{sp_host}" f":5432/msbudget?sslmode=require"
)




check_paused_deepscraping_sql = os.path.dirname(deepscraping_views.__file__) + "/check_paused_deepscraping.sql"
check_running_deepscraping_sql = os.path.dirname(deepscraping_views.__file__) + "/check_running_deepscraping.sql"
start_deepscraping_db_sql = os.path.dirname(deepscraping_views.__file__) + "/start_deepscraping.sql"
stop_deepscraping_db_sql = os.path.dirname(deepscraping_views.__file__) + "/stop_deepscraping.sql"
