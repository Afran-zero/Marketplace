FROM apache/airflow:2.9.0-python3.12

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    DO_NOT_TRACK=1

USER airflow

RUN pip install --no-cache-dir \
    pyspark==3.5.1 \
    boto3 \
    apache-airflow-providers-amazon