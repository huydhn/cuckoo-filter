FROM centos:7

RUN yum clean all

RUN yum install -y https://archive.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm || echo 'OK'
RUN yum groupinstall -y 'Development Tools'

RUN yum install -y pandoc python34-pylint
RUN yum install -y python34-devel python34-setuptools python34-unittest2 python34-coverage python34-nose python34-pip

RUN pip3.4 install netaddr mmh3 bitarray

RUN yum install -y rubygems ruby-devel
RUN gem install fpm
