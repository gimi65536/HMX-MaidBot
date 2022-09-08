FROM python:3.10

WORKDIR /tmp

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]