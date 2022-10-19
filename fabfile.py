"""
Treeshop: The Treehouse Workshop

Experimental fabric based automation to process samples on a docker-machine cluster.

NOTE: This is crafted code primarily used internal to Treehouse and assumes
quite a few things about the layout of primary and secondary files both
on a shared file server and object store. If you are not familiar with
any of these it is recommended to stick with the Makefile for sample by sample
processing on the command line.

Storage Hierarchy:

Samples and outputs are managed on disk or S3 with the following hierarchy:

primary/
    original/
        id/
           *.fastq.gz, *.fq.gz, *.txt.gz or *.bam
           (multiple fastq pairs will be concatenated)
    derived/
        id/
           *.fastq.gz

downstream/
    id/
        secondary/
            pipeline-name-version-hash/
        tertiary/

NOTE: See Makefile for regex that looks from right for 1 or 2 to find pairs

"""
import os
import datetime
import json
import glob
import re
from fabric.api import env, local, run, sudo, runs_once, parallel, warn_only, cd, settings
from fabric.operations import put, get

# To debug communication issues un-comment the following
# import logging
# logging.basicConfig(level=logging.DEBUG)

"""
Setup the fabric hosts environment using docker-machine ip addresses as hostnames are not
resolvable. Also point to all the per machine ssh keys. An alternative would be to use one key but
on openstack the driver deletes it on termination.
"""


def _find_machines():
    """ Fill in host globals from docker-machine """
    env.user = "ubuntu"
    machines = [json.loads(open(m).read())["Driver"]
                for m in glob.glob(os.path.expanduser("~/.docker/machine/machines/*/config.json"))]
    env.hostnames = [m["MachineName"] for m in machines
                     if not env.hosts or m["MachineName"] in env.hosts]
    env.hosts = [m["IPAddress"] for m in machines
                 if not env.hosts or m["MachineName"] in env.hosts]
    # Use single key due to https://github.com/UCSC-Treehouse/pipelines/issues/5
    # env.key_filename = [m["SSHKeyPath"] for m in machines]
    env.key_filename = "~/.ssh/id_rsa"


_find_machines()


def _log_error(message):
    print(message)
    with open("errors.txt", "a") as error_log:
        error_log.write(message + "\n")

@runs_once
def up(count=1):
    """ Spin up 'count' docker machines """
    print("Spinning up {} more cluster machines".format(count))
    for i in range(int(count)):
        hostname = "{}-treeshop-{:%Y%m%d-%H%M%S}".format(
            os.environ["USER"], datetime.datetime.now())
        # Create a new keypair per machine due to https://github.com/docker/machine/issues/3261
        # Custom engine-install-url to install an older version; otherwise, it tries to install package docker-compose-plugin
        # which causes a crash
        local("""
              docker-machine create --driver openstack \
              --engine-install-url https://raw.githubusercontent.com/docker/docker-install/e5f4d99c754ad5da3fc6e060f989bb508b26ebbd/install.sh \
              --openstack-tenant-id 41e142e18a07427caf61ed29652c8c08 \
              --openstack-auth-url http://controller:5000/v3/ \
              --openstack-domain-id default \
              --openstack-ssh-user ubuntu \
              --openstack-net-name treehouse-net \
              --openstack-floatingip-pool ext-net \
              --openstack-image-name ubuntu-16.04-LTS-x86_64 \
              --openstack-flavor-name m1.large \
              {}
              """.format(hostname))
        # Copy over single key due to https://github.com/UCSC-Treehouse/pipelines/issues/5
        local("cat ~/.ssh/id_rsa.pub" +
              "| docker-machine ssh {} 'cat >> ~/.ssh/authorized_keys'".format(hostname))

    # In case additional commands are called after up
    _find_machines()

@runs_once
def unlock():
    """Copy your SSH key to all machines"""
    for hostname in env.hostnames:
        print("Copying SSH key to {}".format(hostname))
        local("cat ~/.ssh/id_rsa.pub" +
              "| docker-machine ssh {} 'cat >> ~/.ssh/authorized_keys'".format(hostname))

@runs_once
def down():
    """ Terminate ALL docker-machine machines """
    for host in env.hostnames:
        print("Terminating {}".format(host))
        local("docker-machine stop {}".format(host))
        local("docker-machine rm -f {}".format(host))


@runs_once
def machines():
    """ Print hostname, ip, and ssh key location of each machine """
    print("Machines:")
    for machine in zip(env.hostnames, env.hosts):
        print("{}/{}".format(machine[0], machine[1]))


def top():
    """ Get list of docker containers """
    run("docker ps")



@parallel
def installdocker():
    """ Install docker on a system with no previous installation"""
    # Use this if "fab up" crashed and docker-machine cannot detect docker.
    # Otherwise, use configure.

    # Set up docker group
    sudo("groupadd docker")
    sudo("gpasswd -a ubuntu docker")
    sudo("apt-get -qy install make")

    # Install toil's preferred docker
    run("wget https://packages.docker.com/1.12/apt/repo/pool/main/d/docker-engine/docker-engine_1.12.6~cs8-0~ubuntu-xenial_amd64.deb")  # NOQA
    sudo("apt-get -y install libltdl7")
    sudo("dpkg -i docker-engine_1.12.6~cs8-0~ubuntu-xenial_amd64.deb")
    sudo("service docker start")

    # Upload the Makefile
    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")

@parallel
def configure():
    """ Copy pipeline makefile over, make directories etc... """
    sudo("gpasswd -a ubuntu docker")
    sudo("apt-get -qy install make")

    """ Downgrade docker to version supported by toil """
    run("wget https://packages.docker.com/1.12/apt/repo/pool/main/d/docker-engine/docker-engine_1.12.6~cs8-0~ubuntu-xenial_amd64.deb")  # NOQA
    sudo("apt-get -y remove docker docker-engine docker.io docker-ce containerd.io docker-ce-cli")
    sudo("rm -rf /var/lib/docker")
    sudo("service docker stop") # Service gets upset if we dpkg the new version while it's still running
    sudo("apt-get -y install libltdl7")
    sudo("dpkg -i docker-engine_1.12.6~cs8-0~ubuntu-xenial_amd64.deb")
    sudo("service docker start")

    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")


@parallel
def push():
    """ Update Makefile for use when iterating and debugging """
    # Copy Makefile in case we changed it while developing...
    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")


@parallel
def reference():
    """ Configure each machine with reference files. """
    put("{}/md5".format(os.path.dirname(env.real_fabfile)), "/mnt")
    with cd("/mnt"):
        run("make reference")

@parallel
def reference_ercc():
    """ Configure each machine with reference files - ERCC version. """
    put("{}/md5".format(os.path.dirname(env.real_fabfile)), "/mnt")
    with cd("/mnt"):
        run("make reference_ercc")


def reset():
    """ Stop any existing processing and delete inputs and outputs """
    print("Resetting {}".format(env.host))
    with warn_only():
        run("docker stop $(docker ps -a -q)")
        run("docker rm $(docker ps -a -q)")
        sudo("rm -rf /mnt/samples/*")
        sudo("rm -rf /mnt/outputs/*")

        # Do we need this? Some pipeline looks like its changing it to root
        sudo("chown -R ubuntu:ubuntu /mnt")


def _put_primary(sample_id, base):
    """ Search all fastqs and bams, convert and put to machine as needed """

    # First see if there are ONLY two fastqs in derived
    files = sorted(glob.glob("{}/primary/derived/{}/*.fastq.gz".format(base, sample_id))
                   + glob.glob("{}/primary/derived/{}/*.fq.gz".format(base, sample_id)))
    if len(files) == 2:
        print("Processing two derived fastqs for {}".format(sample_id))
        for fastq in files:
            print("Copying fastq {} to cluster machine....".format(fastq))
            put(fastq, "/mnt/samples/")
        return files

    # Look for fastqs in primary
    files = sorted(glob.glob("{}/primary/original/{}/*.txt.gz".format(base, sample_id))
                   + glob.glob("{}/primary/original/{}/*.fastq.gz".format(base, sample_id))
                   + glob.glob("{}/primary/original/{}/*.fq.gz".format(base, sample_id)))

    # Two primary fastqs
    if len(files) == 2:
        print("Processing two primary fastqs for {}".format(sample_id))
        for fastq in files:
            print("Copying fastq {} to cluster machine....".format(fastq))
            put(fastq, "/mnt/samples/")
        return files

    # More then two original fastqs so concatenate
    if len(files) > 2 and len(files) % 2 == 0:
        print("Converting multiple primary fastqs for {}".format(sample_id))
        for fastq in files:
            print("Copying fastq {} to cluster machine....".format(fastq))
            put(fastq, "/mnt/samples/")
        names = [os.path.basename(f) for f in files]
        print("Names:", names)
        print("Concatenating fastqs...")
        with cd("/mnt/samples"):
            run("zcat {} | gzip > merged.R1.fastq.gz".format(" ".join(names[0::2])))
            run("zcat {} | gzip > merged.R2.fastq.gz".format(" ".join(names[1::2])))
            run("rm {}".format(" ".join(names)))  # Free up space
        return files

    # No fastqs so look for a single bam in original
    files = sorted(glob.glob("{}/primary/original/{}/*.bam".format(base, sample_id)))
    if len(files) == 1:
        print("Converting original bam for {}".format(sample_id))
        bam = os.path.basename(files[0])
        put(files[0], "/mnt/samples/")
        with cd("/mnt/samples"):
            run("docker run --rm"
                " -v /mnt/samples:/data"
                " -e input={}"
                " linhvoyo/btfv9"
                "@sha256:44f5c116f9a4a89e1fc49c6ec5aec86a9808e856f7fd125509dfe7e011f5ef59".format(bam)) # NOQA
            run("rm *.bam")  # Free up space
        local("mkdir -p {}/primary/derived/{}".format(base, sample_id))
        print("Copying fastqs back for archiving")
        get("/mnt/samples/*.log", "{}/primary/derived/{}/".format(base, sample_id))
        fastqs = get("/mnt/samples/*.fastq.gz", "{}/primary/derived/{}/".format(base, sample_id))
        return fastqs

    print("ERROR Unable to find or derive secondary input for {}".format(sample_id))
    return []


def _fusions(base, output, methods, sample_id, fastqs):
    """Calculate fusion from fastq files"""
    methods["start"] = datetime.datetime.utcnow().isoformat()
    with settings(warn_only=True):
        result = run("cd /mnt && make fusions")
        if result.failed:
            _log_error("{} Failed fusions: {}".format(sample_id, result))
            return False

    # Might generate FusionInspector.junction_reads.bam, FusionInspector.spanning_reads.bam
    # If these are present, store them in primary/derived as they contain sequence data
    with settings(warn_only=True):
        with cd("/mnt/outputs/fusions"):
            result = run("mv -v FusionInspector.*_reads.bam ..")
    if result.failed:
        bamdest = False
        print("Can't move FusionInspector bam files for {}; assume not generated.".format(sample_id))
    else:
        bamdest = "{}/primary/derived/{}".format(base, sample_id)
        local("mkdir -p {}".format(bamdest))

    # Update methods.json and copy output back, including bams to bamdest if present
    dest = "{}/ucsctreehouse-fusion-0.1.0-3faac56".format(output)
    local("mkdir -p {}".format(dest))
    methods["inputs"] = fastqs
    methods["outputs"] = [
        os.path.relpath(p, base) for p in get("/mnt/outputs/fusions/*", dest)]
    if bamdest:
        methods["outputs"] += [
            os.path.relpath(p, base) for p in get("/mnt/outputs/FusionInspector.*_reads.bam", bamdest)]
    methods["end"] = datetime.datetime.utcnow().isoformat()
    methods["pipeline"] = {
        "source": "https://github.com/UCSC-Treehouse/fusion",
        "docker": {
            "url": "https://hub.docker.com/r/ucsctreehouse/fusion",
            "version": "0.1.0",
            "hash": "sha256:3faac562666363fa4a80303943a8f5c14854a5f458676e1248a956c13fb534fd" # NOQA
        }
    }
    with open("{}/methods.json".format(dest), "w") as f:
        f.write(json.dumps(methods, indent=4))

    # And move the FusionInspector files back to fusions dir.
    if bamdest:
        with cd("/mnt/outputs/fusions"):
            run("mv -v ../FusionInspector.*_reads.bam .")

    return True


def _jfkm(base, output, methods, sample_id, fastqs):
    """Calculate jfkm"""
    methods["start"] = datetime.datetime.utcnow().isoformat()
    with settings(warn_only=True):
        result = run("cd /mnt && make jfkm")
        if result.failed:
            _log_error("{} Failed jfkm: {}".format(sample_id, result))
            return False

    # Update methods.json and copy output back, omitting counts.jf by moving it temporarily
    with cd("/mnt/outputs/jfkm"):
        run("mv counts.jf ..")
    dest = "{}/jpfeil-jfkm-0.1.0-26350e0".format(output)
    local("mkdir -p {}".format(dest))
    methods["inputs"] = fastqs
    methods["outputs"] = [
        os.path.relpath(p, base) for p in get("/mnt/outputs/jfkm/*", dest)]
    methods["end"] = datetime.datetime.utcnow().isoformat()
    methods["pipeline"] = {
        "source": "https://github.com/UCSC-Treehouse/jfkm",
        "docker": {
            "url": "https://cloud.docker.com/repository/docker/jpfeil/jfkm",
            "version": "0.1.0",
            "hash": "sha256:26350e02608115341fe8e735ef6d08216e71d962b176eb53b9a7bc54ef715c10" # NOQA
        }
    }
    with open("{}/methods.json".format(dest), "w") as f:
        f.write(json.dumps(methods, indent=4))
    with cd("/mnt/outputs/jfkm"):
        run("mv ../counts.jf .")
    return True


def _pizzly(base, output, methods, sample_id):
    """
    Run the Pizzly docker on a single sample and backhaul pizzly-fusion.final
    Expects that expression Kallisto output is available in pwd/outputs/expression/Kallisto
    """
    methods["start"] = datetime.datetime.utcnow().isoformat()
    with settings(warn_only=True):
        result = run("cd /mnt && make pizzly")
        if result.failed:
            _log_error("{} Failed pizzly: {}".format(sample_id, result))
            return False

    # Update methods.json and copy pizzly-fusion.final file back
    dest = "{}/pizzly-0.37.3-43efb2f".format(output)
    local("mkdir -p {}".format(dest))
    kallisto_dest = "{}/ucsc_cgl-rnaseq-cgl-pipeline-3.3.4-785eee9/Kallisto".format(
        os.path.relpath(output, base))
    methods["inputs"] = ["{}/abundance.h5".format(kallisto_dest),
                         "{}/fusion.txt".format(kallisto_dest)]
    methods["outputs"] = [
        os.path.relpath(p, base) for p in get("/mnt/outputs/pizzly/pizzly-fusion.final", dest)]
    methods["end"] = datetime.datetime.utcnow().isoformat()
    methods["pipeline"] = {
        "source": "https://github.com/UCSC-Treehouse/docker-pizzly",
        "docker": {
            "url": "https://hub.docker.com/r/ucsctreehouse/pizzly",
            "version": "0.37.3",
            "hash": "sha256:43efb2faf95f9d6bfd376ce6b943c9cf408fab5c73088023d633e56880ac1ea8" # NOQA
        }
    }
    with open("{}/methods.json".format(dest), "w") as f:
        f.write(json.dumps(methods, indent=4))
    return True

@parallel
def one_docker(manifest="manifest.tsv", base=".", checksum_only="False"):
    """
        Run a single docker step for all ids listed in 'manifest.'
        Doesn't do any setup or cleanup. This is for testing new dockers on existing output
    """
    with open(manifest) as f:
        sample_ids = sorted([word.strip() for line in f.readlines() for word in line.split(',')
                             if word.strip()])[env.hosts.index(env.host)::len(env.hosts)]

    for sample_id in sample_ids:
        print("{} Running one {}".format(env.host, sample_id))

        # Intialize fake fastqs - this is only for printing to methods
        # The inner docker finds fastqs via the Makefile
        fastqs = [ "PLACEHOLDER-PATH/placeholder_R1.fastq.gz", "PLACEHOLDER-PATH/placeholder_R2.fastq.gz"]

        # Initialize methods.json and output
        methods = { "note" : "This is a test output file!" }
        output = "{}/downstream/{}/secondary".format(base, sample_id)
        local("mkdir -p {}".format(output))

        # Run your docker here
        _jfkm(base, output, methods, sample_id, fastqs)


@parallel
def fusion(manifest="manifest.tsv", base="."):
    """ Set up the fastq files and run the fusion step only for all IDs listed in manifest"""

    # Copy Makefile in case we changed it while developing...
    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")

    # Read ids and pick every #hosts to allocate round robin to each machine
    with open(manifest) as f:
        sample_ids = sorted([word.strip() for line in f.readlines() for word in line.split(',')
                             if word.strip()])[env.hosts.index(env.host)::len(env.hosts)]

    for sample_id in sample_ids:

        # Set up the sample fastqs and output dir
        setup_ok, methods, fastqs, output = _setup(sample_id, base)
        if not setup_ok:
            continue

        # And run fusion only.
        if not _fusions(base, output, methods, sample_id, fastqs):
            continue


def _setup(sample_id, base):
    """ Preprocessing step for a single sample. Upload fastqs, setup methods dict,
        create output dir.
        Returns success status, base methods dict, fastqs, output."""
    print("{} processing {}".format(env.host, sample_id))

    # Reset machine clearing all output, samples, and killing dockers
    reset()

    run("mkdir -p /mnt/samples")

    # Put secondary input files from primary storage
    fastqs = _put_primary(sample_id, base)
    print("Original fastq paths", fastqs)
    fastqs = [os.path.relpath(fastq, base) for fastq in fastqs]
    print("Relative fastq paths", fastqs)

    if not fastqs:
        _log_error("Unable find any fastqs or bams associated with {}".format(sample_id))
        return (False, False, False, False)

    # Create downstream output parent
    output = "{}/downstream/{}/secondary".format(base, sample_id)
    local("mkdir -p {}".format(output))

    # Initialize methods.json
    methods = {"user": os.environ["USER"],
               "treeshop_version": local(
                  "git --work-tree={0} --git-dir {0}/.git describe --always".format(
                      os.path.dirname(__file__)), capture=True),
               "sample_id": sample_id}

    return (True, methods, fastqs, output)

@parallel
def process(manifest="manifest.tsv", base=".", checksum_only="False", ercc="False"):
    """ Process all ids listed in 'manifest' """

    # Copy Makefile in case we changed it while developing...
    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")

    # Read ids and pick every #hosts to allocate round robin to each machine
    with open(manifest) as f:
        sample_ids = sorted([word.strip() for line in f.readlines() for word in line.split(',')
                             if word.strip()])[env.hosts.index(env.host)::len(env.hosts)]

    for sample_id in sample_ids:

        # Set up the sample fastqs and output dir
        setup_ok, methods, fastqs, output = _setup(sample_id, base)
        if not setup_ok:
            continue

        # Begin running pipelines

        # Calculate checksums
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make checksums")
            if result.failed:
                _log_error("{} Failed checksums: {}".format(sample_id, result))
                continue

        # Update methods.json and copy output back
        dest = "{}/md5sum-3.7.0-ccba511".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = fastqs
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/checksums/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/gliderlabs/docker-alpine",
            "docker": {
                "url": "https://hub.docker.com/alpine",
                "version": "3.7.0",
                "hash": "sha256:ccba511b1d6b5f1d83825a94f9d5b05528db456d9cf14a1ea1db892c939cda64" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        if checksum_only == "True":
            continue

        # Calculate expression
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            if ercc:
                result = run("cd /mnt && make expression_ercc")
            else:
                result = run("cd /mnt && make expression")
            if result.failed:
                _log_error("{} Failed expression: {}".format(sample_id, result))
                continue

        # Unpack outputs and normalize names so we don't have sample id in them
        with cd("/mnt/outputs/expression"):
            run("tar -xvf *.tar.gz --strip 1")
            run("rm *.tar.gz")
            run("mv *.sorted.bam sorted.bam")

        # Temporarily move sorted.bam and Kallisto/fusion.txt to parent dir so we don't download it
        # Still pretty hacky but prevents temporary exposure of sequence data to downstream dir
        with cd("/mnt/outputs/expression"):
            run("mv sorted.bam ..")
            run("mv Kallisto/fusion.txt ..")

        # Update methods.json and copy output back
        if ercc:
            dest = "{}/ucsc_cgl-rnaseq-cgl-pipeline-ERCC-3.3.4-785eee9".format(output)
        else:
            dest = "{}/ucsc_cgl-rnaseq-cgl-pipeline-3.3.4-785eee9".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = fastqs
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/expression/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/BD2KGenomics/toil-rnaseq",
            "docker": {
                "url": "https://quay.io/ucsc_cgl/rnaseq-cgl-pipeline",
                "version": "3.3.4-1.12.3",
                "hash": "sha256:785eee9f750ab91078d84d1ee779b6f74717eafc09e49da817af6b87619b0756" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        # Move sorted.bam back to the expression dir so that QC can find it;
        # and Kallisto/fusion.txt for pizzly
        with cd("/mnt/outputs/expression"):
            run("mv ../sorted.bam .")
            run("mv ../fusion.txt Kallisto")

        # Calculate qc (bam-umend-qc)
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            if ercc:
                result = run("cd /mnt && make qc_ercc")
            else:
                result = run("cd /mnt && make qc")
            if result.failed:
                _log_error("{} Failed qc: {}".format(sample_id, result))
                continue

        # Store sortedByCoord.md.bam and .bai in primary/derived
        # First, move it out of the way momentarily so it won't get
        # downloaded into downstream
        bamdest = "{}/primary/derived/{}".format(base, sample_id)
        local("mkdir -p {}".format(bamdest))
        with cd("/mnt/outputs/qc"):
            run("mv sortedByCoord.md.bam* ..")

        # Update methods.json and copy output back
        if ercc:
            dest = "{}/ucsctreehouse-bam-mend-qc-v2.0.2-1c3c627".format(output)
            local("mkdir -p {}".format(dest))
            methods["inputs"] = ["{}/ucsc_cgl-rnaseq-cgl-pipeline-ERCC-3.3.4-785eee9/sorted.bam".format(
                os.path.relpath(output, base))]
        else:
            dest = "{}/ucsctreehouse-bam-umend-qc-1.1.1-5f286d7".format(output)
            local("mkdir -p {}".format(dest))
            methods["inputs"] = ["{}/ucsc_cgl-rnaseq-cgl-pipeline-3.3.4-785eee9/sorted.bam".format(
                    os.path.relpath(output, base))]

        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/qc/*", dest)]

        # Download the bams to primary/derived. Hardlink ERCC bams to sortedByCoord.md.ERCC.bam before
        # downloading those ERCC bams only so that they don't clobber any pre-existing non-ERCC bams.
        if ercc:
            with cd("/mnt/outputs"):
                run("ln -v sortedByCoord.md.bam sortedByCoord.md.ERCC.bam")
                run("ln -v sortedByCoord.md.bam.bai sortedByCoord.md.ERCC.bam.bai")
            methods["outputs"] += [
                os.path.relpath(p, base) for p in get("/mnt/outputs/sortedByCoord.md.ERCC.bam*", bamdest)]
         else:
            methods["outputs"] += [
                os.path.relpath(p, base) for p in get("/mnt/outputs/sortedByCoord.md.bam*", bamdest)]

        methods["end"] = datetime.datetime.utcnow().isoformat()
        if ercc:
            methods["pipeline"] = {
                "source": "https://github.com/UCSC-Treehouse/mend_qc/releases/tag/v2.0.2",
                "docker": {
                    "url": "https://hub.docker.com/r/ucsctreehouse/bam-mend-qc/",
                    "version": "v2.0.2",
                    "hash": "sha256:1c3c62731eb7e6bbfcba4600807022e250a9ee5874477d115939a5d33f39e39f" # NOQA
                }
            }
        else:
            methods["pipeline"] = {
                "source": "https://github.com/UCSC-Treehouse/bam-umend-qc",
                "docker": {
                    "url": "https://hub.docker.com/r/ucsctreehouse/bam-umend-qc",
                    "version": "1.1.1",
                    "hash": "sha256:5f286d72395fcc5085a96d463ae3511554acfa4951aef7d691bba2181596c31f" # NOQA
                }
            }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        # And move the QC bam back so it's available to the variant caller
        with cd("/mnt/outputs/qc"):
            run("mv ../sortedByCoord.md.bam* .")

        # Calculate pizzly from Kallisto results
        if not _pizzly(base, output, methods, sample_id):
            continue

        # Calculate fusion
        if not _fusions(base, output, methods, sample_id, fastqs):
            continue

        # Calculate jfkm from fastq files
        if not _jfkm(base, output, methods, sample_id, fastqs):
            continue

        # Calculate variants
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make variants")
            if result.failed:
                _log_error("{} Failed variants: {}".format(sample_id, result))
                continue

        # Update methods.json and copy output back
        dest = "{}/ucsctreehouse-mini-var-call-0.0.1-1976429".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = ["{}/sortedByCoord.md.bam".format(bamdest)]
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/variants/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/UCSC-Treehouse/mini-var-call",
            "docker": {
                "url": "https://hub.docker.com/r/ucsctreehouse/mini-var-call",
                "version": "0.0.1",
                "hash": "sha256:197642937956ae73465ad2ef4b42501681ffc3ef07fecb703f58a3487eab37ff" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))
