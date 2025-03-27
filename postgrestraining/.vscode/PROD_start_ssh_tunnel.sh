#!/bin/bash

# # Start the SSH tunnel
# ssh -L 1433:sqlserver-cdh-datahub-cp-01.database.windows.net:1433 turek.r@pg.com@137.181.62.138 -p 22
# ssh -L 5432:az-postgres-ers-nonprod-01.postgres.database.azure.com:5432 turek.r@137.181.62.10 -p 22
ssh -L 5432:psql-pg-az-postgres-ers-prodflexibe-01.postgres.database.azure.com:5432 turek.r@137.181.62.10 -p 22
