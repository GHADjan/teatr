FROM python:3.10

WORKDIR /botname

COPY ./requirements.txt /botname/requirements.txt

RUN pip install -r /botname/requirements.txt

COPY . /botname/

CMD ["python3.10", "app.py"]
#CMD python3 /botname/app.py


