FROM centos:7 AS env

# change default shell to bash
SHELL ["/bin/bash", "-c"] 

RUN yum -y update | /bin/true

RUN groupadd --gid 808 scitech-group
RUN useradd --gid 808 --uid 550 --create-home --password '$6$ouJkMasm5X8E4Aye$QTFH2cHk4b8/TmzAcCxbTz7Y84xyNFs.gqm/HWEykdngmOgELums1qOi3e6r8Z.j7GEA9bObS/2pTN1WArGNf0' scitech

# Configure Sudo
RUN echo -e "scitech ALL=(ALL)       NOPASSWD:ALL\n" >> /etc/sudoers

# From maestro container setup
RUN yum install -y \
            epel-release \
            centos-release-scl-rh

# These had installation problems, so I've grouped them together before others
RUN yum install -y \
            devtoolset-9         \
            git-lfs              \
            pkg-config           \
            golang               \
            inotify-tools        \
            lxc                  \
            osg-ca-certs         \
            osg-wn-client        \
            python36-future      \
            python36-pika        \
            python36-pyOpenSSL   \
            python36-pytest      \
            python36-PyYAML      \
            R-devel              \
            singularity          \
            boost169-devel       

# 
RUN yum install -y ant | /bin/true
RUN yum install -y \
            automake libtool gdb doxygen \
            lib*san \
            ant-apache-regexp \
            ant-junit \
            bc \
            bzip2-devel \
            ca-certificates \
            cryptsetup \
            epel-release \
            file \
            gcc-gfortran \
            graphviz \
            graphviz-devel-2.30.1-22.el7.x86_64 \
            hwloc hwloc-devel numactl-devel cmake3 \
            ImageMagick \
            iptables \
            java-1.8.0-openjdk \
            java-1.8.0-openjdk-devel \
            libffi-devel \
            libjpeg-turbo-devel \
            libseccomp-devel \
            libuuid-devel \
            make \
            mpich-devel \
            mysql-devel \
            openjpeg-devel \
            openssl-devel \
            patch \
            postgresql-devel \
            python36-devel \
            python36-pip \
            python36-setuptools \
            readline-devel \
            rpm-build \
            sqlite-devel \
            sudo \
            squashfs-tools \
            tar \
            unzip \
            vim \
            wget \
            which \
            yum-plugin-priorities \
            zlib-devel \
    && yum clean all \
    && rm -rf /var/cache/yum/*

# Docker + Docker in Docker setup
RUN curl -sSL https://get.docker.com/ | sh
ADD ./config/wrapdocker /usr/local/bin/wrapdocker
RUN chmod +x /usr/local/bin/wrapdocker
VOLUME /var/lib/docker
RUN usermod -aG docker scitech

# Python packages
RUN pip3 install wheel tox six sphinx recommonmark sphinx_rtd_theme sphinxcontrib-openapi javasphinx jupyter jupyterlab astropy MontagePy GitPython breathe
# need most recent pyyaml
RUN pip3 install -U PyYAML networkx pandas matplotlib pygraphviz pydot ipyplot graphviz wand web-pdb

# Montage (using newly installed gcc-9)
RUN cd /opt \
    && source /opt/rh/devtoolset-9/enable \
    && wget -nv http://montage.ipac.caltech.edu/download/Montage_v6.0.tar.gz \
    && tar xzf Montage_v6.0.tar.gz \
    && rm -f Montage_v6.0.tar.gz \
    && cd Montage \
    && make

# Set Timezone
RUN cp /usr/share/zoneinfo/Europe/Zurich /etc/localtime

# Get Condor yum repo
RUN curl -o /etc/yum.repos.d/condor.repo https://research.cs.wisc.edu/htcondor/yum/repo.d/htcondor-stable-rhel7.repo
RUN rpm --import https://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor
RUN yum -y install condor minicondor
RUN sed -i 's/condor@/scitech@/g' /etc/condor/config.d/00-minicondor

RUN usermod -a -G condor scitech
RUN chmod -R g+w /var/{lib,log,lock,run}/condor

RUN chown -R scitech /home/scitech/

RUN echo -e "condor_master > /dev/null 2>&1" >> /home/scitech/.bashrc

# User setup
USER scitech

WORKDIR /home/scitech

# Set up config for ensemble manager
RUN mkdir /home/scitech/.pegasus \
    && echo -e "#!/usr/bin/env python3\nUSERNAME='scitech'\nPASSWORD='scitech123'\n" >> /home/scitech/.pegasus/service.py \
    && chmod u+x /home/scitech/.pegasus/service.py

# Get Pegasus 
RUN git clone https://github.com/pegasus-isi/pegasus.git --depth 1 --branch 5.0 --single-branch \
    && cd pegasus \
    && ant dist \
    && cd dist \
    && mv $(find . -type d -name "pegasus-*") pegasus

# setup PATH, include pegasus, mpich, montage
ENV PATH /home/scitech/pegasus/dist/pegasus/bin:$HOME/.pyenv/bin:$PATH:/usr/lib64/mpich/bin:/opt/Montage/bin
ENV PYTHONPATH /home/scitech/pegasus/dist/pegasus/lib64/python3.6/site-packages

# Set up pegasus database
RUN /home/scitech/pegasus/dist/pegasus/bin/pegasus-db-admin create

# build maestro (using gcc-9)
RUN git clone https://gitlab.jsc.fz-juelich.de/maestro/maestro-core.git \
  &&  source /opt/rh/devtoolset-9/enable \
  &&  cd maestro-core   \
  &&  autoreconf -ifv   \
  && ./configure --prefix=/home/scitech/maestro \
  &&  make install

# Build mocktage from cpp-cdo branch if no MOCKTAGE_SHA supplied
ARG MOCKTAGE_SHA=cpp-cdo
ENV MOCKTAGE_BRANCH $MOCKTAGE_SHA

RUN if [[ -z "$MOCKTAGE_SHA" ]] ; then echo "No mocktage branch, using $MOCKTAGE_SHA"; else echo "Using branch $MOCKTAGE_SHA" ; fi && MOCKTAGE_BRANCH=$MOCKTAGE_SHA

RUN git clone https://gitlab.jsc.fz-juelich.de/maestro/mocktage.git \
  && source /opt/rh/devtoolset-9/enable \
  && sudo ln -s /usr/bin/cmake3 /usr/bin/cmake \
  && cd mocktage \
  && git checkout $MOCKTAGE_SHA \
  && mkdir build \
  && cd build \
  && cmake -DMaestro_ROOT=/home/scitech/maestro -DMOCKTAGE_WITH_CPP=ON -DBOOST_INCLUDEDIR=/usr/include/boost169 -DBOOST_LIBRARYDIR=/usr/lib64/boost169 -DCMAKE_EXE_LINKER_FLAGS='-lrdmacm -libverbs' .. \
  && make -j4

# Set Kernel for Jupyter (exposes PATH and PYTHONPATH for use when terminal from jupyter is used)
ADD ./config/kernel.json /usr/local/share/jupyter/kernels/python3/kernel.json
RUN echo -e "export PATH=/home/scitech/pegasus/dist/pegasus/bin:/home/scitech/.pyenv/bin:\$PATH:/usr/lib64/mpich/bin:/opt/Montage/bin" >> /home/scitech/.bashrc
RUN echo -e "export PYTHONPATH=/home/scitech/pegasus/dist/pegasus/lib64/python3.6/site-packages" >> /home/scitech/.bashrc

# Set notebook password to 'scitech'. This pw will be used instead of token authentication
#RUN mkdir /home/scitech/.jupyter \ 
#    && echo "{ \"NotebookApp\": { \"password\": \"sha1:30a323540baa:6eec8eaf3b4e0f44f2f2aa7b504f80d5bf0ad745\" } }" >> /home/scitech/.jupyter/jupyter_notebook_config.json

# Set notebook password to 'maestro'. This pw will be used instead of token authentication
RUN mkdir /home/scitech/.jupyter \ 
    && echo "{ \"NotebookApp\": { \"password\": \"argon2:\$argon2id\$v=19\$m=10240,t=10,p=8\$y1o4HI0QrKhN9axmVBGncw\$rZ4OEHoDSLJhQJw6r83uUA\" } }" >> /home/scitech/.jupyter/jupyter_notebook_config.json

# set default theme for Jupyter lab to Dark
RUN mkdir -p ~/.jupyter/lab/user-settings/\@jupyterlab/apputils-extension/ \
    && echo '{ "theme":"JupyterLab Dark" } ' >> /home/scitech/.jupyter/lab/user-settings/\@jupyterlab/apputils-extension/themes.jupyterlab-settings
RUN mkdir -p ~/.jupyter/lab/user-settings/\@jupyterlab/terminal-extension/ \
    && echo '{ "scrollback": 5000 }        ' >> /home/scitech/.jupyter/lab/user-settings/\@jupyterlab/terminal-extension/plugin.jupyterlab-settings

# wrapdocker required for nested docker containers
ENTRYPOINT ["sudo", "/usr/local/bin/wrapdocker"]
CMD ["su", "-", "scitech", "-c", "jupyter lab --notebook-dir=/home/scitech/shared-data --port=8888 --no-browser --ip=0.0.0.0 --allow-root"] 

# load environment for gcc-9 (might not stick in user env)
RUN source /opt/rh/devtoolset-9/enable
