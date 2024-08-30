set -e
echo '>>> Docker Run for : IOTpoll '
docker build -f dockerfile --network=host --tag iotpoll .
#docker login --username leerobo --password Winter1970.
#docker tag vincent-$1 docker.io/leerobo/IOTpoll:IOTpoll
#docker image push leerobo/vincent-$1:vincent
