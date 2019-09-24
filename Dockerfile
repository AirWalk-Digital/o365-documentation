FROM python
COPY . /app
RUN cd /app && pip install -r requirements_all.txt
RUN cp -f /app/config.py.sample /app/config.py
WORKDIR /app
CMD python run_flask.py
