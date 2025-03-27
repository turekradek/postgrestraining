import os.path

# OLD CODE FROM LEGACY VM

from db_config import configuration as config
from os import environ

is_local = environ.get("IS_LOCAL", "").lower() == "true"
user = environ.get("DB_USER", "postgres")
password = environ.get("DB_PASSWORD", environ.get("radek"))
# db
db_host = (
    "localhost"
    if is_local
    else environ.get("DB_SERVER", "localhost")
)
db_host_vm = "localhost" if is_local else "localhost"
db_port = environ.get("DB_PORT", "5433")
db_name = environ.get("DB_NAME", "greencycles")
# db_flags = environ.get("DB_FLAGS", "?sslmode=require")
# db_flags = "" if db_flags.lower() == "no_flags" else db_flags

db_url = f"postgresql://{user}:{password}@{db_host}:{db_port}/{db_name}{db_flags}"
db_url_vm = f"postgresql://{user}:{password}@{db_host_vm}:{db_port}/{db_name}{db_flags}"


stop_deepscraping_db_sql = os.path.dirname(config.__file__) + "/check_table.sql"
