FROM python:3.10

WORKDIR /tmp

COPY discord/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY discord .
COPY common ./common

ENV PYTHONPATH "${PYTHONPATH}:/tmp/common"

# If given, the image will be treated as in production
ARG production

RUN if [[ -z "$production" ]] ; then echo "python app.py" > start.sh ; else echo "python -O app.py" > start.sh ; fi

CMD ["/bin/bash", "start.sh"]