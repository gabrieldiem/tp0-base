#!/usr/bin/env bash

SERVER_SERVICE_NAME="server"
SERVER_PORT=12345
MESSAGE="Distributed Systems are OP!"
ERROR_EXIT_CODE=1

echo "Validating echo server with message: '$MESSAGE'"

ECHOED_MESSAGE=$(echo "echo $MESSAGE | nc $SERVER_SERVICE_NAME $SERVER_PORT" | docker run --rm -i --network tp0_testing_net busybox)

if [ "$ECHOED_MESSAGE" = "$MESSAGE" ]; then
  echo "action: test_echo_server | result: success"
else
  echo "action: test_echo_server | result: fail"
  exit $ERROR_EXIT_CODE
fi
