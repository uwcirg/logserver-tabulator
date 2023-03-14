# logserver_tabulator
Named after the late great reporter logserver_tabulator Ifill, `logserver_tabulator` works in concert with `logserver`
 to generate project specific reports.

## How To Run
As a flask application, `logserver_tabulator` exposes HTTP routes as well as a number of command line
interface entry points.

These instructions assume a docker-compose deployment.  Simply eliminate the leading
`docker-composed exec` portion of each command if deployed outside a docker container.

To view available HTTP routes:
```
docker-compose exec logserver_tabulator flask routes
```

To view available CLI entry points:
```
docker-compose exec logserver_tabulator flask --help
```
