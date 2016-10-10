.. _install-from-conda:

Installing ARTIQ
================

The preferred way of installing ARTIQ is through the use of the conda package manager.
The conda package contains pre-built binaries that you can directly flash to your board.

.. warning::
    NIST users on Linux need to pay close attention to their ``umask``.
    The sledgehammer called ``secureconfig`` leaves you (and root) with umask 027 and files created by root (for example through ``sudo make install``) inaccessible to you.
    The usual umask is 022.


.. warning::
    Conda packages are supported for Linux (64-bit) and Windows (32- and 64-bit).
    Users of other operating systems (32-bit Linux, BSD, OSX ...) should and can :ref:`install from source <install-from-source>`.


Installing Anaconda or Miniconda
--------------------------------

You can either install Anaconda (choose Python 3.5) from https://store.continuum.io/cshop/anaconda/ or install the more minimalistic Miniconda (choose Python 3.5) from http://conda.pydata.org/miniconda.html

After installing either Anaconda or Miniconda, open a new terminal (also known as command line, console, or shell and denoted here as lines starting with ``$``) and verify the following command works::

    $ conda

Executing just ``conda`` should print the help of the ``conda`` command [1]_.

Installing the ARTIQ packages
-----------------------------

Add the M-Labs ``main`` Anaconda package repository containing stable releases and release candidates to your conda configuration::

    $ conda config --add channels http://conda.anaconda.org/m-labs/label/main

.. note::
    To use the development versions of ARTIQ, also add the ``dev`` label (http://conda.anaconda.org/m-labs/label/dev).
    Development versions are built for every change and contain more features, but are not as well-tested and are more likely to contain more bugs or inconsistencies than the releases in the ``main`` label.

Then prepare to create a new conda environment with the ARTIQ package and the matching binaries for your hardware:
choose a suitable name for the environment, for example ``artiq-main`` if you intend to track the main label or ``artiq-2016-04-01`` if you consider the environment a snapshot of ARTIQ on 2016-04-01.
Choose the package containing the binaries for your hardware:

    * ``artiq-pipistrello-nist_qc1`` for the `Pipistrello <http://pipistrello.saanlima.com/>`_ board with the NIST adapter to SCSI cables and AD9858 DDS chips.
    * ``artiq-kc705-nist_qc1`` for the `KC705 <http://www.xilinx.com/products/boards-and-kits/ek-k7-kc705-g.html>`_ board with the NIST adapter to SCSI cables and AD9858 DDS chips.
    * ``artiq-kc705-nist_clock`` for the KC705 board with the NIST "clock" FMC backplane and AD9914 DDS chips.
    * ``artiq-kc705-nist_qc2`` for the KC705 board with the NIST QC2 FMC backplane and AD9914 DDS chips.

Conda will create the environment, automatically resolve, download, and install the necessary dependencies and install the packages you select::

    $ conda create -n artiq-main artiq-pipistrello-nist_qc1

After the installation, activate the newly created environment by name.
On Unix::

    $ source activate artiq-main

On Windows::

    $ activate artiq-main

This activation has to be performed in every new shell you open to make the ARTIQ tools from that environment available.

.. note::
    [Linux] The ``qt5`` package requires libraries not packaged under the ``m-labs`` conda labels.
    Those need to be installed through the Linux distribution's mechanism.
    If GUI programs do not start because they ``could not find or load the Qt platform plugin "xcb"``, install the various ``libxcb-*`` packages through your distribution's preferred mechanism.
    The names of the libraries missing can be obtained from the output of a command like ``ldd [path-to-conda-installation]/envs/artiq-main/lib/qt5/plugins/platform/libqxcb.so``.

.. note::
    Some ARTIQ examples also require matplotlib and numba, and they must be installed manually for running those examples. They are available in conda.


Upgrading ARTIQ
---------------

When upgrading ARTIQ or when testing different versions it is recommended that new environments are created instead of upgrading the packages in existing environments.
Keep previous environments around until you are certain that they are not needed anymore and a new environment is known to work correctly.
You can create a new conda environment specifically to test a certain version of ARTIQ::

    $ conda create -n artiq-test-1.0rc2 artiq-pipistrello-nist_qc1=1.0rc2

Switching between conda environments using ``$ source deactivate artiq-1.0rc2`` and ``$ source activate artiq-1.0rc1`` is the recommended way to roll back to previous versions of ARTIQ.
You can list the environments you have created using::

    $ conda env list

See also the `conda documentation <http://conda.pydata.org/docs/using/envs.html>`_ for managing environments.

Preparing the core device FPGA board
------------------------------------

You now need to write three binary images onto the FPGA board:

1. The FPGA gateware bitstream
2. The BIOS
3. The ARTIQ runtime

They are all shipped in the conda packages, along with the required flash proxy gateware bitstreams.

.. _install-openocd:

Installing OpenOCD
^^^^^^^^^^^^^^^^^^

OpenOCD can be used to write the binary images into the core device FPGA board's flash memory. It can be installed using conda on both Linux and Windows::

    $ conda install openocd

Some additional steps are necessary to ensure that OpenOCD can communicate with the FPGA board.

On Linux, first ensure that the current user belongs to the ``plugdev`` group. If it does not, run ``sudo adduser $USER plugdev`` and relogin. Afterwards::

    $ wget https://raw.githubusercontent.com/ntfreak/openocd/406f4d1c68330e3bf8d9db4e402fd8802a5c79e2/contrib/99-openocd.rules
    $ sudo cp 99-openocd.rules /etc/udev/rules.d
    $ sudo adduser $USER plugdev
    $ sudo udevadm trigger

On Windows, a third-party tool, `Zadig <http://zadig.akeo.ie/>`_, is necessary. Use it as follows:

1. Make sure the FPGA board's JTAG USB port is connected to your computer.
2. Activate Options → List All Devices.
3. Select the "Digilent Adept USB Device (Interface 0)" (for KC705) or "Pipistrello LX45" (for Pipistrello) device from the drop-down list.
4. Select WinUSB from the spinner list.
5. Click "Install Driver" or "Replace Driver".

You may need to repeat these steps every time you plug the FPGA board into a port where it has not been plugged into previously on the same system.

Then, you can flash the board:

* For the Pipistrello board::

    $ artiq_flash -t pipistrello -m nist_qc1

* For the KC705 board (selecting the appropriate hardware peripheral)::

    $ artiq_flash -t kc705 -m [nist_qc1/nist_clock/nist_qc2]

  The SW13 switches also need to be set to 00001.

For the KC705, the next step is to flash the MAC and IP addresses to the board. See :ref:`those instructions <flash-mac-ip-addr>`.


Configuring the core device
---------------------------

This should be done after either installation method (conda or source).

.. _flash-mac-ip-addr:

* Set the MAC and IP address in the :ref:`core device configuration flash storage <core-device-flash-storage>`:

    * You can set it through JTAG by generating a flash storage image and then flashing it: ::

        $ artiq_mkfs flash_storage.img -s mac xx:xx:xx:xx:xx:xx -s ip xx.xx.xx.xx
        $ artiq_flash -f flash_storage.img proxy storage start

    * Or, if you have a serial connection ready, you can set it via the runtime test mode command line

        * Boot the board.

        * Quickly run flterm (in ``path/to/misoc/tools``) to access the serial console.

        * If you weren't quick enough to see anything in the serial console, press the reset button.

        * Wait for "Press 't' to enter test mode..." to appear and hit the ``t`` key.

        * Enter the following commands (which will erase the flash storage content).

            ::

                test> fserase
                test> fswrite ip xx.xx.xx.xx
                test> fswrite mac xx:xx:xx:xx:xx:xx

        * Then reboot.

        You should see something like this in the serial console: ::

            $ ./tools/flterm --port /dev/ttyUSB1
            [FLTERM] Starting...

            MiSoC BIOS   http://m-labs.hk
            (c) Copyright 2007-2014 Sebastien Bourdeauducq
            [...]
            Press 't' to enter test mode...
            Entering test mode.
            test> fserase
            test> fswrite ip 192.168.10.2
            test> fswrite mac 11:22:33:44:55:66

.. note:: The reset button of the KC705 board is the "CPU_RST" labeled button.
.. warning:: Both those instructions will result in the flash storage being wiped out. However you can use the test mode to change the IP/MAC without erasing everything if you skip the "fserase" command.

* (optional) You may also want to set ``netmask`` and ``gateway`` in the same way that you set ``ip``.

* (optional) Flash the idle kernel

The idle kernel is the kernel (some piece of code running on the core device) which the core device runs whenever it is not connected to a PC via ethernet.
This kernel is therefore stored in the :ref:`core device configuration flash storage <core-device-flash-storage>`.
To flash the idle kernel:

        * Compile the idle experiment:
                The idle experiment's ``run()`` method must be a kernel: it must be decorated with the ``@kernel`` decorator (see :ref:`next topic <connecting-to-the-core-device>` for more information about kernels).

                Since the core device is not connected to the PC, RPCs (calling Python code running on the PC from the kernel) are forbidden in the idle experiment.
                ::

                $ artiq_compile idle.py

        * Write it into the core device configuration flash storage: ::

                $ artiq_coreconfig write -f idle_kernel idle.elf

.. note:: You can find more information about how to use the ``artiq_coreconfig`` utility on the :ref:`Utilities <core-device-configuration-tool>` page.

* (optional) Flash the startup kernel

The startup kernel is executed once when the core device powers up. It should initialize DDSes, set up TTL directions, etc. Proceed as with the idle kernel, but using the ``startup_kernel`` key in ``artiq_coreconfig``.

* (optional) Select the startup clock

The core device may use either an external clock signal or its internal clock. This clock can be switched dynamically after the PC is connected using the ``external_clock`` parameter of the core device driver; however, one may want to select the clock at power-up so that it is used for the startup and idle kernels. Use one of these commands: ::

    $ artiq_coreconfig write -s startup_clock i  # internal clock (default)
    $ artiq_coreconfig write -s startup_clock e  # external clock


.. rubric:: Footnotes

.. [1] [Linux] If your shell does not find the ``conda`` command, make sure that the conda binaries are in your ``$PATH``:
       If ``$ echo $PATH`` does not show the conda directories, add them: execute ``$ export PATH=$HOME/miniconda3/bin:$PATH`` if you installed conda into ``~/miniconda3``.
