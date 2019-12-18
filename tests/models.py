# coding: utf-8
from sqlalchemy import Column, ForeignKey, String, INTEGER
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from talos.db import dictbase

Base = declarative_base()
metadata = Base.metadata


class Address(Base, dictbase.DictBase):
    __tablename__ = 'address'

    id = Column(String(36), primary_key=True)
    location = Column(String(63), nullable=False)
    user_id = Column(ForeignKey(u'user.id', ondelete=u'CASCADE', onupdate=u'CASCADE'), nullable=False)

    user = relationship(u'User')


class Department(Base, dictbase.DictBase):
    __tablename__ = 'department'

    id = Column(String(36), primary_key=True)
    name = Column(String(63), nullable=False)


class User(Base, dictbase.DictBase):
    __tablename__ = 'user'
    attributes = ['id', 'name', 'department_id', 'age', 'department', 'addresses']
    detail_attributes = attributes
    summary_attributes = ['id', 'name', 'department_id', 'age']

    id = Column(String(36), primary_key=True)
    name = Column(String(63), nullable=False)
    department_id = Column(ForeignKey(u'department.id', ondelete=u'RESTRICT', onupdate=u'RESTRICT'), nullable=False)
    age = Column(INTEGER, nullable=True)

    department = relationship(u'Department', lazy=False)
    addresses = relationship(u'Address', lazy=False, back_populates=u'user', uselist=True, viewonly=True)


class Business(Base, dictbase.DictBase):
    __tablename__ = 'business'
    attributes = ['id', 'name', 'owner_dep_id', 'create_user_id', 'owner_dep', 'create_user']
    detail_attributes = attributes
    summary_attributes = ['id', 'name', 'owner_dep_id', 'create_user_id']

    id = Column(String(36), primary_key=True)
    name = Column(String(63), nullable=False)
    owner_dep_id = Column(ForeignKey(u'department.id', ondelete=u'RESTRICT', onupdate=u'RESTRICT'), nullable=False)
    create_user_id = Column(ForeignKey(u'user.id', ondelete=u'RESTRICT', onupdate=u'RESTRICT'), nullable=False)

    owner_dep = relationship(u'Department', lazy=False)
    create_user = relationship(u'User', lazy=False)
