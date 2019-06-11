FROM centos:7

RUN yum clean all

RUN yum install -y https://archive.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm || echo 'OK'
RUN yum groupinstall -y 'Development Tools'

RUN yum install -y pandoc python36-pylint
RUN yum install -y python36-devel python36-setuptools python36-unittest2 python36-coverage python36-nose python36-pip

RUN pip3.6 install netaddr mmh3 bitarray

RUN yum install -y rubygems ruby-devel
RUN gem install fpm
