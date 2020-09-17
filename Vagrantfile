# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Apache webserver
  config.vm.network "forwarded_port", guest: 80, host: 8089
  config.vm.network "forwarded_port", guest: 8088, host: 8088

  # If true, then any SSH connections made will enable agent forwarding.
  config.ssh.forward_agent = true

  # Never sync the current directory to /vagrant.
  config.vm.synced_folder ".", "/vagrant", disabled: true

  checkout = "yes"
  if ENV['CHECKOUT'] != 'y' then
    checkout = "no"
  end

  config.vm.provider "virtualbox" do |vb, override|
    vb.gui = false
    vb.memory = 2048
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate//vagrant","0"]
    if ENV['CHECKOUT'] != 'y' then
      override.vm.synced_folder ".", "/home/vagrant/Nominatim"
    end
  end

  config.vm.provider "libvirt" do |lv, override|
    lv.memory = 2048
    lv.nested = true
    if ENV['CHECKOUT'] != 'y' then
      override.vm.synced_folder ".", "/home/vagrant/Nominatim", type: 'nfs'
    end
  end

  config.vm.define "ubuntu", primary: true do |sub|
      sub.vm.box = "generic/ubuntu2004"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-20.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "ubuntu-apache" do |sub|
      sub.vm.box = "generic/ubuntu2004"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-20.sh"
        s.privileged = false
        s.args = [checkout, "install-apache"]
      end
  end

  config.vm.define "ubuntu-nginx" do |sub|
      sub.vm.box = "generic/ubuntu2004"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-20.sh"
        s.privileged = false
        s.args = [checkout, "install-nginx"]
      end
  end

  config.vm.define "ubuntu18" do |sub|
      sub.vm.box = "generic/ubuntu1804"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-18.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "ubuntu18-apache" do |sub|
      sub.vm.box = "generic/ubuntu1804"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-18.sh"
        s.privileged = false
        s.args = [checkout, "install-apache"]
      end
  end

  config.vm.define "ubuntu18-nginx" do |sub|
      sub.vm.box = "generic/ubuntu1804"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Ubuntu-18.sh"
        s.privileged = false
        s.args = [checkout, "install-nginx"]
      end
  end

  config.vm.define "centos7" do |sub|
      sub.vm.box = "centos/7"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Centos-7.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "centos" do |sub|
      sub.vm.box = "generic/centos8"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/Install-on-Centos-8.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end


end
