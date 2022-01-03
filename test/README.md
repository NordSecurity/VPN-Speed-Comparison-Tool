# How to test your changes.
## Manual testing (just bare minimum)
Just few things from all code to test:
1. Test if all docker images builds successfully:
```sh
$ cd docker
$ ./dockerBuild.sh rebuild all
```
2. Check if daemon is not broken and if its possible to start it.
```sh
$ cd ./docker
$ docker-compose up -d
 ``` 
3. Check if test can accept configuration and run. (Edit and validate configuration before executing: `docker-compose up`)
 ```sh
$ docker-compose exec runner vpnspeed up /opt/vpnspeed/vpnspeed.yaml
 ``` 
4. Try to generate report 
```sh
$ docker-compose exec runner vpnspeed report
```


## Auto Testing
This is still a new project, so there aren't many tests. To run them execute:
```sh
$ python3 -m unittest discover -s test
```
