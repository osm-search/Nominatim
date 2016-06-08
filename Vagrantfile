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

  config.vm.define "ubuntu" do |sub|
      sub.vm.box = "bento/ubuntu-16.04"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/install-on-ubuntu-16.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  config.vm.define "centos" do |sub|
      sub.vm.box = "bento/centos-7.2"
      sub.vm.provision :shell do |s|
        s.path = "vagrant/install-on-centos-7.sh"
        s.privileged = false
        s.args = [checkout]
      end
  end

  # configure shared package cache if possible
  #if Vagrant.has_plugin?("vagrant-cachier")
  #  config.cache.enable :apt
  #  config.cache.scope = :box
  #end


  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.customize ["modifyvm", :id, "--memory", "2048"]
  end


  # config.vm.provider :digital_ocean do |provider, override|
  #   override.ssh.private_key_path = '~/.ssh/id_rsa'
  #   override.vm.box = 'digital_ocean'
  #   override.vm.box_url = "https://github.com/smdahlen/vagrant-digitalocean/raw/master/box/digital_ocean.box"

  #   provider.token = ''
  #   # provider.token = 'YOUR TOKEN'
  #   provider.image = 'ubuntu-14-04-x64'
  #   provider.region = 'nyc2'
  #   provider.size = '512mb'
  # end

end
