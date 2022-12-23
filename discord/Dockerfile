FROM python:3.11

WORKDIR /tmp

# Install requirements for this repo
RUN pip install poetry
RUN poetry config virtualenvs.create false

COPY discord/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/pyproject.toml common/poetry.lock ./common
RUN cd ./common && poetry install --only main

COPY SimpleCalculator/pyproject.toml SimpleCalculator/poetry.lock ./SimpleCalculator
RUN cd ./SimpleCalculator && poetry install --only main

# Install submodules
COPY common ./common
RUN cd ./common && poetry install
RUN rm -rf ./common

COPY SimpleCalculator ./SimpleCalculator
RUN cd ./SimpleCalculator && poetry install
RUN rm -rf ./SimpleCalculator

COPY discord .

# Give it to enable optimization
ARG optimize

RUN if [[ -z "$optimize" ]] ; then echo "python -u app.py" > start.sh ; else echo "python -u -O app.py" > start.sh ; fi

CMD ["/bin/bash", "start.sh"]
