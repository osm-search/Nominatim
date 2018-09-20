# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Apache webserver
  config.vm.network "forwarded_port", guest: 80, host: 8089

  # If true, then any SSH connections made will enable agent forwarding.
  config.ssh.forward_agent = true

  checkout = "yes"
  if ENV['CHECKOUT'] != 'y' then
      config.vm.synced_folder ".", "/home/vagrant/Nominatim"
      checkout = "no"
  end

  config.vm.define "ubuntu", primary: true do |sub|
      sub.vm.box = "bento/ubuntu-18.04"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-18.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "ubuntu18nginx" do |sub|
      sub.vm.box = "bento/ubuntu-18.04"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-18-nginx.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "ubuntu16" do |sub|
      sub.vm.box = "bento/ubuntu-16.04"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-16.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "travis" do |sub|
      sub.vm.box = "bento/ubuntu-14.04"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/install-on-travis-ci.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "centos" do |sub|
      sub.vm.box = "centos/7"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Centos-7.sh"
        s.privileged = false
        s.args = "yes"
      end
      sub.vm.synced_folder ".", "/home/vagrant/Nominatim", disabled: true
      sub.vm.synced_folder ".", "/vagrant", disabled: true
  end

  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = 2048
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate//vagrant","0"]
  end

end
