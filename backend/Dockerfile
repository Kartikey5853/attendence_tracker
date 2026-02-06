# Use slim Python
FROM python:3.12-slim

RUN apt-get update && apt-get install -y wget gnupg unzip ca-certificates && rm -rf /var/lib/apt/lists/*

# Install Chrome for Testing
RUN wget -O /tmp/chrome-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chrome-linux64.zip && \
    unzip /tmp/chrome-linux64.zip -d /opt && \
    ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome && \
    rm /tmp/chrome-linux64.zip

# Install matching Chromedriver
RUN wget -O /tmp/chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.122/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver-linux64.zip -d /opt && \
    ln -s /opt/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver-linux64.zip

ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER=/usr/local/bin/chromedriver

WORKDIR /app
COPY backend/ /app/
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
