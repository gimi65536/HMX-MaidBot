FROM python:3.11 as base

WORKDIR /tmp

FROM base as builder

# Install requirements for this repo

# Install poetry and venv
RUN pip install --no-cache-dir poetry
RUN python -m venv /venv

COPY discord/requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

COPY common/pyproject.toml common/poetry.lock ./common/
RUN cd ./common && poetry env use /venv/bin/python && poetry install --no-root

COPY SimpleCalculator/pyproject.toml SimpleCalculator/poetry.lock ./SimpleCalculator/
RUN cd ./SimpleCalculator && poetry env use /venv/bin/python && poetry install --no-root

# Install submodules
COPY common ./common
RUN cd ./common && /venv/bin/pip install .

COPY SimpleCalculator ./SimpleCalculator
RUN cd ./SimpleCalculator && /venv/bin/pip install .

FROM base as final

COPY --from=builder /venv /venv
ENV PATH="/venv/bin:${PATH}"
ENV VIRTUAL_ENV="/venv"

COPY discord .

# Give it to enable optimization
ARG optimize

RUN if [[ -z "$optimize" ]] ; then echo "python -u app.py" > start.sh ; else echo "python -u -O app.py" > start.sh ; fi

CMD ["/bin/bash", "start.sh"]
