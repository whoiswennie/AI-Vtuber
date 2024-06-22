@echo off
set OLD_NEO4J_HOME=%NEO4J_HOME%
set OLD_JAVA_HOME=%JAVA_HOME%
set NEO4J_HOME=
set JAVA_HOME=%JAVA_HOME15%
set SCRIPT_DIR=%~dp0
cd %SCRIPT_DIR%\bin
start "" neo4j.bat console
echo Neo4j 数据库已启动。
set NEO4J_HOME=%OLD_NEO4J_HOME%
set JAVA_HOME=%OLD_JAVA_HOME%
exit
