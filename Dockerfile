FROM python:3.10-slim

WORKDIR /app
COPY . /app

# Silence pip root warning
ENV PIP_ROOT_USER_ACTION=ignore

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install playwright & browsers
RUN pip install playwright && playwright install --with-deps

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]

