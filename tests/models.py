import logging
from django.db import models

class MockHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
        }


class Office(models.Model):
    location = models.CharField(max_length=50)


class Title(models.Model):
    name = models.CharField(max_length=50)
    salary = models.IntegerField(null=True)
    boss = models.NullBooleanField(default=False)


class Employee(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    title = models.ForeignKey(Title, null=True)
    office = models.ForeignKey(Office)
    is_manager = models.NullBooleanField(default=False)


class Meeting(models.Model):
    attendees = models.ManyToManyField(Employee)
    office = models.ForeignKey(Office)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)


class Project(models.Model):
    name = models.CharField(max_length=50)
    employees = models.ManyToManyField(Employee)
    manager = models.OneToOneField(Employee, related_name='managed_projects')
    due_date = models.DateField(null=True)
