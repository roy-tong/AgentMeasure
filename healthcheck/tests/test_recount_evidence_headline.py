import unittest
from verovo_healthcheck.vendors import recount,recount_report
class TestEvidenceHeadline(unittest.TestCase):
    def report(self,rows):
        return recount_report(recount({'records':rows,'columns_missing':[]},'intercom'))
    def test_all_unknown_zero_is_not_clearance(self):
        report=self.report([{'vendor_billed':True}])
        self.assertIn('Unsettled rows: 1/1',report)
        self.assertIn('zero identified variance is not a cleared bill',report)
        self.assertIn('not a verified invoice total or refund',report)
    def test_underbilling_is_not_called_negative_overcharge(self):
        report=self.report([dict(vendor_billed=False,human_agent_participated=False,issue_addressed=True,customer_recontacted_within_window=False)])
        self.assertIn('identified net variance: USD -0.99',report)
        self.assertNotIn('net overcharge',report)
