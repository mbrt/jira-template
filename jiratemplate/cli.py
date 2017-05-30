#!/usr/bin/env python

"""Jira Template

Usage:
  jiratemplate create [options] [-o <opt>]... <summary>
  jiratemplate get [options] <id>
  jiratemplate list (vars | sections) [options]
  jiratemplate (-h | --help)
  jiratemplate --version

Options:
  -h --help                     Show this screen.
  --version                     Show version.

  -V --verbose                  Enable debug logs.
  --dry-run                     Do not execute any request to jira.

  -c <file>, --config=<file>    Specify the config file
                                [default: ~/.jira-template/conf.yaml].
  -t <file>, --template=<file>  Specify the template file
                                [default: ~/.jira-template/template.json].
  -s <sec>, --section=<sec>     Specify the config file section to be used for
                                the variables.
  -o <opt>, --option=<opt>      Override a value in the template.
"""
import base64
import json
import logging
import os
import re
import sys

from docopt import docopt
import editor
import requests
import yaml

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger("jiratemplate")


def die(msg):
    print(msg)
    sys.exit(1)


def parse_yaml(yfile):
    with open(yfile) as f:
        return yaml.load(f)


def parse_json(jfile):
    with open(jfile) as f:
        return json.loads(f.read())


class IssueConf:
    def __init__(self, conf, template, opts, secname):
        self.conf = conf
        self.template = template
        self.opts = opts
        self.secname = secname

    def get_final_conf(self):
        fields = {}
        if self.secname:
            try:
                fields = next(f for f in self.conf["sections"] if f["id"] == self.secname)
            except:
                raise Exception("cannot find section {} in config".format(self.secname))
        # merge with custom options
        fields.update(self.opts)
        res = self.template.copy()
        IssueConf._replace_conf(res, fields)
        return res

    def _replace_conf(template, values):
        to_remove = []
        for e in template.items():
            (key, val) = e
            if isinstance(val, str) and val.startswith("$"):
                newval = values.get(val[1:])
                if newval is None:
                    # remove not replaced variables
                    to_remove.append(key)
                else:
                    template[key] = newval
            elif isinstance(val, dict):
                IssueConf._replace_conf(val, values)
                # remove empty dictionaries
                if len(val) == 0:
                    to_remove.append(key)
        for e in to_remove:
            log.debug("field {} removed because the value was not given".format(e))
            template.pop(e)


class JiraRest:
    def __init__(self, endpoint, user, pwd, dry_run=False):
        self.endpoint = endpoint
        self.user = user
        self.pwd = pwd
        self.dry_run = dry_run

    def create(self, data):
        return self._post("/rest/api/2/issue/", data)

    def get(self, ticket):
        return self._get("/rest/api/2/issue/{}".format(ticket))

    def _post(self, path, data):
        url = "{}{}".format(self.endpoint, path)
        if self.dry_run:
            return {
                "type": "POST",
                "url": url,
                "request": data,
            }
        r = requests.post(url, json=data, auth=(self.user, self.pwd))
        if r.status_code >= 300 or r.status_code < 200:
            raise Exception("Cannot post to jira, error {}, data {}".format(r.status_code, r.text))
        return r.json()

    def _get(self, path):
        url = "{}{}".format(self.endpoint, path)
        if self.dry_run:
            return {
                "type": "GET",
                "url": url,
            }
        r = requests.get(url, auth=(self.user, self.pwd))
        if r.status_code != 200:
            raise Exception("Cannot get from jira, error {}, data {}".format(r.status_code, r.text))
        return r.json()


def jira_rest(conf, dry_run):
    return JiraRest(conf["address"],
                    conf["username"],
                    base64.b64decode(conf["password"]).decode("utf-8"),
                    dry_run)


def create(summary, conf_file, template_file, section_name=None, options={}, dry_run=False):
    conf = parse_yaml(conf_file)
    template = parse_json(template_file)
    log.debug("conf file: {}".format(conf))
    log.debug("template file: {}".format(template))
    descr = editor.edit(contents=b"Please replace here the description")
    opts = {
        "summary": summary,
        "description": bytes.decode(descr),
    }
    opts.update(options)
    log.debug("options: {}".format(opts))
    issueconf = IssueConf(conf, template, opts, section_name)
    rconf = issueconf.get_final_conf()
    log.debug("resulting config: {}".format(rconf))
    jira = jira_rest(conf, dry_run)
    res = jira.create(rconf)

    # print results
    if dry_run:
        # different format when dry run
        print("{} {}".format(res["type"], res["url"]))
        print(json.dumps(res["request"], indent=2))
    else:
        print(json.dumps(res, indent=2))
        print("Browse to: {}/browse/{}".format(conf["address"], res["key"]))


def get_vars_in_template(template, varlist):
    for e in template.items():
        (key, val) = e
        if isinstance(val, str) and val.startswith("$"):
            varlist.append(val[1:])
        elif isinstance(val, dict):
            get_vars_in_template(val, varlist)


def list_vars(template_file):
    template = parse_json(template_file)
    log.debug("template file: {}".format(template))
    varlist = []
    get_vars_in_template(template, varlist)
    for v in varlist:
        print(v)


def list_sections(conf_file):
    conf = parse_yaml(conf_file)
    log.debug("conf file: {}".format(conf))
    for s in conf["sections"]:
        print(s["id"])


def get(ticket_id, conf_file, dry_run=False):
    conf = parse_yaml(conf_file)
    jira = jira_rest(conf, dry_run)
    res = jira.get(ticket_id)
    if dry_run:
        # different format when dry run
        print("{} {}".format(res["type"], res["url"]))
    else:
        print(json.dumps(res, indent=2))


def init_logger(verbose):
    if verbose:
        log.setLevel(logging.DEBUG)


def replace_home(val):
    if os.environ["HOME"]:
        return val.replace('~', os.environ["HOME"])
    return val


def parse_custom_opts(args):
    opts = {}
    for opt in args:
        m = re.match("^([^=]+)=(.*)$", opt)
        if m:
            opts[m.group(1)] = m.group(2)
        else:
            log.debug("invalid custom option: {}".format(opt))
    log.debug("custom options: {}".format(opts))
    return opts


def main():
    args = docopt(__doc__, version="Jira Template 0.1")
    init_logger(args["--verbose"])
    log.debug(args)

    try:
        # commands
        if args["create"]:
            create(args["<summary>"],
                   replace_home(args["--config"]),
                   replace_home(args["--template"]),
                   args["--section"],
                   parse_custom_opts(args["--option"]),
                   args["--dry-run"])
        elif args["get"]:
            get(args["<id>"], replace_home(args["--config"]), args["--dry-run"])
        elif args["list"] and args["vars"]:
            list_vars(replace_home(args["--template"]))
        elif args["list"] and args["sections"]:
            list_sections(replace_home(args["--config"]))
        else:
            die("command not found??")
    except Exception as e:
        die("Error: {}".format(str(e)))


if __name__ == "__main__":
    main()
