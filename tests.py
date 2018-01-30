import unittest
import box_office

class BoxOfficeTest(unittest.TestCase):
    def test_from_url_format_date(self):
        url = 'https://tickets.fandango.com/transaction/ticketing/express/ticketboxoffice.aspx?row_count=210902271&tid=AAVPA&sdate=2018-01-25+14:45&mid=202672&from=mov_det_showtimes'
        assert box_office.get_time_date(url)[0] == '2018-01-25'
         
    def test_from_url_format_time(self):
        url = 'https://tickets.fandango.com/transaction/ticketing/express/ticketboxoffice.aspx?row_count=210902271&tid=AAVPA&sdate=2018-01-25+14:45&mid=202672&from=mov_det_showtimes'
        assert box_office.get_time_date(url)[1] == '14:45'
