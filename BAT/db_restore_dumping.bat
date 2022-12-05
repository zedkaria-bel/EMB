cd %POSTGRES_BIN%
.\psql.exe --dbname=%EMBAPP_DB_NAME% --host=%EMBAPP_DB_HOST% --port=%EMBAPP_DB_PORT% --username=%EMBAPP_DB_USERNAME% < %EMBAPP_DB_SQL_FILE%