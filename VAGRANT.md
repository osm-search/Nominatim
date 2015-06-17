# Install Nominatim in a virtual machine for development and testing

This documention describes how you can install Nominatim inside a Ubuntu 14
virtual machine on your desktop/laptop (host machine). The goal is to give
you a development environment to easily edit code and run the test suite
without affecting the rest of your system. 

The installation runs largely unsupervised, you should expect 1-2h from
start to finish depending on how fast your computer and download speed
is.

# Prerequisites

* Virtualbox
    
    `https://www.virtualbox.org/wiki/Downloads`
    
* install Vagrant

   `https://www.vagrantup.com/downloads.html`

If you plan to destory and re-create the virtual machine often (e.g. to
test the Nominatim installation itself), then [vagrant-cashier](https://github.com/fgrehm/vagrant-cachier)



1. Nominatim

10min

! git clone --recursive https://github.com/twain47/Nominatim.git
otherwise
git submodule init
git submodule update

 a Ubuntu 12.04 LTS 64bit box as basis on
    your machine (yes others would work, too)

   `vagrant box add hashicorp/precise64 --provider virtualbox`



without data!

## Installation

Installing everything into a virtual machine is the fastest method and
mirrors the production environment best. Installation on MacOS or Linux
directly will also work but won't be discussed here.

3. make sure you have a Ubuntu 12.04 LTS 64bit box as basis on
    your machine (yes others would work, too)

   `vagrant box add hashicorp/precise64 --provider virtualbox`

4. download the chorehat code


/vagrant/vagrant-provision.sh



option 1 

give more memory


cd ~/Nominatim


## psql postgres -c "DROP DATABASE IF EXISTS nominatim"
time utils/setup.php --osm-file data/monaco.osm.pbf --osm2pgsql-cache 1000 --all | tee monaco.$$.log
./utils/specialphrases.php --countries > data/specialphrases_countries.sql
psql -d nominatim -f data/specialphrases_countries.sql



option 2




remote database
ssh -L 9999:localhost:5432 ubuntu@api.opencagedata.com



5. create the virtual machine

    `vagrant up && vagrant ssh`



## Development


ssh -L 9999:localhost:5432 ubuntu@your-server.com

http://localhost:8089/nominatim/

## Running tests

    @mtm
    Scenario: address lookup for non-existing or invalid node, way, relation


~/Nominatim/tests$ NOMINATIM_SERVER=http://localhost:8089/nominatim lettuce -t mtm
cd tests
NOMINATIM_SERVER=http://localhost:8089/nominatim lettuce features


settins/locl.php
   @define('CONST_Debug', false);

/var/log/apache2/other_vhosts_access.log




## FAQ

* I don't like VMs

* wil the results be the same as openstreetmap.org?


wikipedia files

can I install the world?

what about MAC/Centos/Linux/FreeBSD?

http://www.vagrantbox.es/




cloud?
digitalocean
only one vm per directory
https://github.com/smdahlen/vagrant-digitalocean
vagrant up --provider digital_ocean --provision




* I want to switch between multiple databases (rename them)

minimum RAM? more RAM?

is there a browser?

can I use VMWare?

32bit?

 ubuntu/trusty64 Official Ubuntu Server 14.04 LTS (Trusty Tahr) builds 






