# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Apache webserver
  config.vm.network "forwarded_port", guest: 8089, host: 8089

  # If true, then any SSH connections made will enable agent forwarding.
  config.ssh.forward_agent = true

  config.vm.synced_folder ".", "/home/vagrant/Nominatim"

  config.vm.define "ubuntu" do |sub|
      sub.vm.box = "ubuntu/trusty64"
      sub.vm.provision :shell, :path => "vagrant/ubuntu-trusty-provision.sh"
  end
  config.vm.define "centos" do |sub|
      sub.vm.box = "bento/centos-7.2"
      sub.vm.provision :shell, :path => "vagrant/centos-7-provision.sh"
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
