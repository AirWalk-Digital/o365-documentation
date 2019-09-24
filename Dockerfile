FROM python
COPY . /app
RUN cd /app && pip install -r requirements_all.txt
CMD python run_flask.py
