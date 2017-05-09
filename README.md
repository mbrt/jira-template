# jira-template
Command line tool for jira, templatizable.

This utility has been tested with Python 3.6, but it's very possible that
it's compatible with previous Python versions as well. The supported Jira
versions are ones providing the `/rest/api/2` endpoint.

## Install
Clone this repository and install its dependencies:

```
git clone https://github.com/mbrt/jira-template.git
cd jira-template
pip install -r requirements.txt
```

## Usage
The command line is available with:

```
python jira-template/jiratemplate/cli.py
```

The idea is pretty simple. After you configure two files: `template.json` and
`conf.yaml`, the utility can be used to create and get tickets from Jira.

## Configuration
Start from the example in `examples/conf.yaml`:

```
mkdir -p ~/.jira-template
cp jira-template/conf.yaml ~/.jira-template/
```
