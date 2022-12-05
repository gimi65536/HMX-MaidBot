FROM python:3.11

WORKDIR /tmp

COPY common ./common
RUN cd ./common && pip install .
RUN rm -rf ./common

COPY discord/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY discord .

# If given, the image will be treated as in production
ARG production

RUN if [[ -z "$production" ]] ; then echo "python -u app.py" > start.sh ; else echo "python -u -O app.py" > start.sh ; fi

CMD ["/bin/bash", "start.sh"]
