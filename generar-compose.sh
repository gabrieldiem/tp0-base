#!/usr/bin/env bash

OUTPUT_FILENAME=$1
NUM_CLIENTS=$2
ERROR_EXIT_CODE=1

DATA_NOMBRE="Santiago Lionel"
DATA_APELLIDO="Lorca"
DATA_DOCUMENTO=30904465
DATA_NACIMIENTO="1999-03-17"
DATA_NUMERO=7574

# Check for both necessary inputs
if [ -z "$OUTPUT_FILENAME" ] || [ -z "$NUM_CLIENTS" ]; then
  echo "Usage: $0 <OUTPUT_FILENAME> <NUMBER_OF_CLIENTS>"
  exit $ERROR_EXIT_CODE
fi

SERVER_SERVICE="
  server:
    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./server/config.ini:/config.ini
    networks:
      - testing_net"

# Write server to file as YAML, which will always be one even if there are n clients
# Truncates (overwrites) if file already exists
echo -e "name: tp0\nservices:$SERVER_SERVICE" > "$OUTPUT_FILENAME"

# Returns the YAML string for a single client taking as first arg the client number
format_client_service() {
  local client_num="$1"
  echo "
  client$client_num:
    container_name: client$client_num
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID=$client_num
      - NOMBRE=$DATA_NOMBRE
      - APELLIDO=$DATA_APELLIDO
      - DOCUMENTO=$DATA_DOCUMENTO
      - NACIMIENTO=$DATA_NACIMIENTO
      - NUMERO=$DATA_NUMERO
    volumes:
      - ./client/config.yaml:/config.yaml
    networks:
      - testing_net
    depends_on:
      - server
"
}

# Append clients to YAML file
for nth_client in $(seq 1 "$NUM_CLIENTS"); do
  client_service=$(format_client_service $nth_client)
  echo "$client_service" >> "$OUTPUT_FILENAME"
done

NETWORK="
networks:
  testing_net:
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24"

# Append the network info to YAML file
echo " $NETWORK" >> "$OUTPUT_FILENAME"

echo "Docker Compose YAML file generated at '$OUTPUT_FILENAME' with $NUM_CLIENTS clients"
