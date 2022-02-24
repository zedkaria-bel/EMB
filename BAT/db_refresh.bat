cd %POSTGRES_BIN%
.\pg_dump.exe --dbname=%EMBAPP_DB_NAME% --host=%EMBAPP_DB_HOST% --port=%EMBAPP_DB_PORT% --username=%EMBAPP_DB_USERNAME% -w --clean > %EMBAPP_DB_SQL_FILE%