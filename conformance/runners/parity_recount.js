#!/usr/bin/env node
/* Parity harness: run the browser-local recount in node and print JSON.
 *
 * The Python parity test (healthcheck/tests/test_parity.py) runs this and
 * compares the result field by field with healthcheck/am_healthcheck/vendors.py
 * on the same fixture. Two implementations of one rule set must not drift.
 *
 * Usage: node parity_recount.js <export.csv> <vendor_id>
 */
"use strict";

var fs = require("fs");
var path = require("path");

var ROOT = path.resolve(__dirname, "..", "..");
var rules = require(path.join(ROOT, "website", "vendor-rules.js"));
var am = require(path.join(ROOT, "website", "recount.js"))(rules);

function main(argv) {
  var exportPath = argv[2];
  var vendorId = argv[3];
  if (!exportPath || !vendorId) {
    process.stderr.write("usage: parity_recount.js <export.csv> <vendor_id>\n");
    return 2;
  }
  var text = fs.readFileSync(exportPath, "utf8");
  var exportData = am.loadExport(text);
  var result = am.recount(exportData, vendorId);
  process.stdout.write(JSON.stringify(result));
  return 0;
}

process.exit(main(process.argv));
