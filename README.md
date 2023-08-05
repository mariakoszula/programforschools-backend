# Backend for Program For Schools
[![CodeFactor](https://www.codefactor.io/repository/github/mariakoszula/programforschools-backend/badge)](https://www.codefactor.io/repository/github/mariakoszula/programforschools-backend)
[![CircleCI](https://dl.circleci.com/status-badge/img/gh/mariakoszula/programforschools-backend/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/mariakoszula/programforschools-backend/tree/main)

* REST API for planning and managing deliveries of product to different schools
* Storing prepared documentation in Google Drive
* Flask based with Docker setup
* Possible deployment with uWSGI on Heroku using heroku.yml

## Requirements for deployment
- Google Drive service account (GOOGLE_DRIVE_AUTH) in config.ini setup GoogleDriveConfig.google_drive_id
- PostgreSQL database (DATABASE_URL)
- Redis server (REDIS_URL)

## REST API 
### Postman collection
```shell
https://grey-sunset-995258.postman.co/workspace/RykoSystem~ee82e97e-50d7-45c3-86eb-49d5962fafdd/collection/22112983-8cc34c88-dc14-4789-bc2f-fd1638332f8b
```

### Running test locally with docker ###
* Change test/config.ini: Database.host=test_db, * Redis.url=redis://redis:6379/0
* pytest.ini redis_host=redis
