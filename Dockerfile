FROM centos:7 AS env

COPY yum_requirements.txt /home/scitech/yum_requirements.txt

RUN set -ex \
    && yum makecache fast \
    && yum -y update \
    && yum -y install epel-release centos-release-scl-rh \
    && yum -y install $(cat /home/scitech/yum_requirements.txt)\
    && yum clean all \
    && rm -rf /var/cache/yum

# change default shell to bash
SHELL ["/bin/bash", "-c"]

RUN echo -e "ulimit -f 900000" >> /etc/bashrc
RUN echo -e "ulimit memlock=-1:-1" >> /etc/bashrc

RUN groupadd --gid 808 scitech-group
RUN useradd --gid 808 --uid 550 --create-home --password '$6$ouJkMasm5X8E4Aye$QTFH2cHk4b8/TmzAcCxbTz7Y84xyNFs.gqm/HWEykdngmOgELums1qOi3e6r8Z.j7GEA9bObS/2pTN1WArGNf0' scitech

# Configure Sudo
RUN echo -e "scitech ALL=(ALL)       NOPASSWD:ALL\n" >> /etc/sudoers

# Python packages
COPY pip_requirements.txt /home/scitech/pip_requirements.txt
RUN pip3 install -U -r /home/scitech/pip_requirements.txt

# Set Timezone
RUN cp /usr/share/zoneinfo/Europe/Zurich /etc/localtime

# Get Condor yum repo
RUN curl -o /etc/yum.repos.d/condor.repo https://research.cs.wisc.edu/htcondor/yum/repo.d/htcondor-stable-rhel7.repo
RUN rpm --import https://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor
RUN yum -y install condor minicondor
RUN sed -i 's/condor@/scitech@/g' /etc/condor/config.d/00-minicondor

# Get Slurm
RUN cd /tmp && \
    wget -q https://github.com/SchedMD/slurm/archive/refs/tags/slurm-20-11-7-1.tar.gz && \
    tar xf slurm-20-11-7-1.tar.gz && \
    cd slurm-slurm-20-11-7-1 && \
    ./configure && \
    make -j && \
    make install

RUN usermod -a -G condor scitech
RUN chmod -R g+w /var/{lib,log,lock,run}/condor

RUN chown -R scitech /home/scitech/

#
# USER LAND
#
USER scitech

WORKDIR /home/scitech

RUN echo -e "condor_master > /dev/null 2>&1" >> /home/scitech/.bashrc

# Pegasus
RUN git clone https://github.com/pegasus-isi/pegasus.git --depth 1 --branch 5.0 --single-branch \
    && cd pegasus \
    && ant dist \
    && cd dist \
    && mv $(find . -type d -name "pegasus-*") pegasus

# Set up pegasus database
RUN /home/scitech/pegasus/dist/pegasus/bin/pegasus-db-admin create

# Maestro
RUN git clone https://gitlab.jsc.fz-juelich.de/maestro/maestro-core.git \
  &&  source /opt/rh/devtoolset-9/enable \
  &&  cd maestro-core   \
  &&  autoreconf -ifv   \
  && ./configure --prefix=/home/scitech/maestro \
  &&  make install

# Montage
RUN source /opt/rh/devtoolset-9/enable \
    && wget -nv http://montage.ipac.caltech.edu/download/Montage_v6.0.tar.gz \
    && tar xzf Montage_v6.0.tar.gz \
    && rm -f Montage_v6.0.tar.gz \
    && cd Montage \
    && make

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

# set default theme for Jupyter lab to Dark
RUN mkdir -p /home/scitech/.jupyter/lab/user-settings/\@jupyterlab/apputils-extension/ \
    && echo '{ "theme":"JupyterLab Dark" }' >> /home/scitech/.jupyter/lab/user-settings/\@jupyterlab/apputils-extension/themes.jupyterlab-settings \
    && mkdir -p /home/scitech/.jupyter/lab/user-settings/\@jupyterlab/terminal-extension/ \
    && echo '{ "scrollback": 5000 }' >> /home/scitech/.jupyter/lab/user-settings/\@jupyterlab/terminal-extension/plugin.jupyterlab-settings \
    && mkdir -p /home/scitech/shared-data \
    && mkdir -p /home/scitech/scratch

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV PATH="/home/scitech/pegasus/dist/pegasus/bin:${PATH}:/usr/lib64/mpich/bin:/home/scitech/Montage/bin"
ENV PYTHONPATH="/home/scitech/pegasus/dist/pegasus/lib64/python3.6/site-packages"

CMD ["jupyter", "lab", "--notebook-dir=/home/scitech/shared-data", "--port=8888", "--no-browser", "--ip=0.0.0.0", "--ServerApp.token=''", "--allow-root" ]

# docker command
# docker run -p 8899:8888 --mount "type=bind,source=$PWD,target=/home/scitech/shared-data" --ulimit memlock=-1:-1 -t biddisco_slurm:1.0
# docker command interactive
# docker run -it -p 8899:8888 --mount "type=bind,source=$PWD,target=/home/scitech/shared-data" --ulimit memlock=-1:-1 -t biddisco_slurm:1.0 /bin/bash
