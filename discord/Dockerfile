FROM python:3.10

WORKDIR /tmp

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# If given, the image will be treated as in production
ARG production

RUN if [[ -z "$production" ]] ; then echo "python -O app.py" > start.sh ; else echo "python app.py" > start.sh ; fi

CMD ["/bin/bash", "start.sh"]