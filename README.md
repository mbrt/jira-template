# jira-template
Command line tool for jira, templatizable.

This utility has been tested with Python 3.6, but it's very possible that
it's compatible with previous Python versions as well. The supported Jira
versions are the ones providing the `/rest/api/2` endpoint.

## Install
Clone this repository and install its dependencies:

```
git clone https://github.com/mbrt/jira-template.git
cd jira-template
pip install -r requirements.txt
```

I recommend creating an alias for the command, something like:

```
alias jtmp='~/jira-template/jiratemplate/cli.py'
```

## Usage
The command line is available with:

```
jira-template/jiratemplate/cli.py
```

The idea is pretty simple. After you configure two files: `template.json` and
`conf.yaml`, the utility can be used to create and get tickets from Jira.

Whenever you create a ticket, you have to specify the summary in the command
line. You can edit the ticket description via the editor that is fired up
afterwards.

## Configuration
Start from the example in `examples/conf.yaml`:

```
mkdir -m 700 -p ~/.jira-template
cp jira-template/conf.yaml ~/.jira-template/
```

Edit it and provide the following informations:

* the server address
* the username
* the password encoded in base64 (you can encode it by using `echo MYPWD | base64 -`)

You can leave the rest as is for the moment.

After you've done this, try to access a ticket number, by using:

```
jtmp get <ticket-id>
```

The result should be a json encoded object that describes the ticket.
Starting from that you can create your own ticket template, like the one
provided in `jira-template/examples/template.json`. I recommend starting from
that example and add only the mandatory fields for your issue types in Jira:

```
cp jira-template/template.json ~/.jira-template/
```

The rules are pretty simple:

* everything that is hardcoded will be sent as is to Jira;
* every value starting with a dollar sign is a variable;
* variables can be templated by a value inside `conf.yaml`; if no matches are
  found, the key-value pair will be left out from the resulting json. This
  can be used for optional fields.

More details on the templating rules are provided in the next section.

## Templating
A template is simply a section in `conf.yaml` with a certain id:

```
sections:
  - id: kube-bug-80
    issue_type: Bug
    versions:
      - id: "11314"
```

You can add as many sections as you want. These will be selected by the create
command with the `-s <section-name>` flag.

For example:

```
jtmp create --dry-run -s kube-bug-80 "this is an ugly bug"
```

will use the section with id `kube-bug-80` to replace the variables in the
`template.json` and fire a request to Jira to create that ticket. Note that the
`--dry-run` flag has been added to print the request without actually creating
the ticket.

Since the configuration file is a yaml, you can leverage its pretty cool
reference mechanism to avoid repeting yourself. For example, with this
reference:

```
templates:
  me: &ME my-username
```

you can avoid repeting your username over and over in all the sections, and
start using the `&ME` reference instead:

```
sections:
  - id: kube-bug-80
    assignee: *ME
```

This is even more powerful, since you can template tickets hierarchically, like
this:

```
templates:
  me: &ME REPLACEME
  dk-account: &KUBE-ACCOUNT 16
  version-80: &VER-80 "11314"
  version-90: &VER-90 "11350"
  kube: &KUBE-ISSUE
    account_id: *KUBE-ACCOUNT
    labels:
      - kubernetes
    assignee: *ME
```

And then provide various sections that reuse the common `KUBE-ISSUE` template:

```
sections:
  - <<: *KUBE-ISSUE
    id: kube-bug-80
    issue_type: Bug
    versions:
      - id: *VER-80
  - <<: *KUBE-ISSUE
    id: kube-bug-90
    issue_type: Bug
    versions:
      - id: *VER-90
```

After the references are resolved, the result is:

```
sections:
  - account_id: 16
    labels:
      - kubernetes
    assignee: my-username
    id: kube-bug-80
    issue_type: Bug
    versions:
      - id: 11314
  - account_id: 16
    labels:
      - kubernetes
    assignee: my-username
    id: kube-bug-90
    issue_type: Bug
    versions:
      - id: 11350
```

A very powerful mechanism.
