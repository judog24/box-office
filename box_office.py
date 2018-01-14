import time
import bs4 as bs
from selenium import webdriver


class Screening:
    def __init__(self, movie_title, screening_type, screening_time, tickets_url):
        self.title = movie_title
        self.type = screening_type
        self.time = screening_time
        self.url = tickets_url
        self.ticket_data = []
        self.seats = {}


def open_browser(url):
    """
    Waits 3 seconds for page to load before performing actions
    """
    browser = webdriver.Firefox()
    browser.get(url)
    time.sleep(3)
    return browser

def get_theaters(file):
    """
    Import theater name and url from file
    """
    theaters = []

    with open(file, 'r') as filestream:
        for line in filestream:
            current_line = line.split(',')
            theater = [current_line[0], current_line[1].rstrip('\n')]
            theaters.append(theater)

    return theaters

def get_showtimes(url):
    """
    Loops through <li> elements with the following general structure:

    <li class="fd-movie">
        <div class="fd-movie__details">
            <a class="dark">Movie Name</a>
        </div>
        <ul class="fd-movie__showtimes">
            <li class="fd-movie__showtimes-variant"> <!-- 3D, XD, Standard -->
                <li class="fd-movie__amenity-icon-wrap>
                    <a data-amenity-name="Reserved seating"></a>
                </li>
                <ol class="fd-movie__btn-list">
                    <li class="fd-movie__btn-list-item">
                    <a class="btn showtime-btn showtime-btn--available" href="ticketURL">time</a>
                    </li>
                </ol>
            </li>
        </ul>
    </li>
    """
    showtimes = []
    browser = open_browser(url)
    soup = bs.BeautifulSoup(browser.page_source, 'lxml')

    movies = soup.find_all('li', {'class': 'fd-movie'})

    for movie in movies:
        movie_title = movie.find('a', {'class': 'dark'}).text

        showtime_types = movie.find_all('li', {'class': 'fd-movie__showtimes-variant'})
        for showtime_type in showtime_types:

            if showtime_type.find('a', {'data-amenity-name': 'Reserved seating'}):

                if showtime_type.find('a', {'data-amenity-name': 'RealD 3D'}):
                    show_type = 'RealD 3D'
                elif showtime_type.find('a', {'data-amenity-name': 'Cinemark XD'}):
                    show_type = 'Cinemark XD'
                elif showtime_type.find('a', {'data-amenity-name': 'Alternative Content'}):
                    show_type = 'Alternative Content'
                elif showtime_type.find('a', {'data-amenity-name': 'IMAX'}):
                    show_type = 'IMAX'
                elif showtime_type.find('a', {'data-amenity-name': 'D-Box'}):
                    show_type = 'D-Box'
                else:
                    show_type = 'Standard'
                showtime_times = showtime_type.find_all('a', {'class': 'showtime-btn--available'})
                for showtime_time in showtime_times:
                    showtimes.append(Screening(movie_title, show_type,
                                               showtime_time.text, showtime_time['href']))
    browser.quit()
    return showtimes

def get_ticket_data(url):
    """
    Parses table with the following general structure:

    <table class="section quantityTable">
        <tbody class="ticketTypeTable" id="Reserved">
            <tr>
                <th class="ticketType">
                    <input type="hidden" name="pricedesc" value="Matinee">
                    <input type="hidden" name="price" value="9.25">
                </th>
                <td class="numberofTickets">
                    <select class="qtyDropDown">
                        <option value="1">1</option>
                    </select>
                </td>
            </tr>
        </tbody>
    </table>
    <h2 id="auditoriumInfo">Auditorium #</h2>
    """
    ticket_types = {}    
    browser = open_browser(url)
    soup = bs.BeautifulSoup(browser.page_source, 'lxml')

    auditorium = soup.find('h2', {'id': 'auditoriumInfo'}).text
    tickets_table = soup.find('table', {'class': 'quantityTable'})
    tickets_rows = tickets_table.find_all('tr')

    for tr in tickets_rows:
        ticket_type = tr.find('input', {'name': 'pricedesc'})
        ticket_price = tr.find('input', {'name': 'price'})
        ticket_types[ticket_type['value']] = ticket_price['value']
    
    ticket_data = [auditorium, ticket_types]
    browser.quit()   
    return ticket_data

def get_seat_data(url):
    """
    Seating chart has the following general strucutre:

    <div id="svg-Layer_1">
        <div id="H16" class="standard availableSeat" data-seats="H16--0"></div>
        <div id="F7" class="standard reservedSeat"></div>
        <div id="D8" class="companion availableSeat"></div>
        <div class="wheelchair availableSeat" id="D11" data-seats="D11-58"></div>
    </div>
    """
    seats_data = {}
    browser = open_browser(url)
    
    select_option = '//*[@id="AreaRepeater_TicketRepeater_0_quantityddl_0"]/option[2]'
    browser.find_element_by_xpath(select_option).click()
    browser.find_element_by_xpath('//*[@id="NewCustomerCheckoutButton"]').click()
    
    seat_soup = bs.BeautifulSoup(browser.page_source, 'lxml')
    seat_chart = seat_soup.find('div', {'id': 'svg-Layer_1'})
    seats = seat_chart.find_all('div')
    for seat in seats:
        seats_data[seat['id']] = seat['class']
    browser.quit()
    return seats_data

def main():
    theaters = get_theaters('theaters_test.txt')
    showtimes = []
    for i, theater in enumerate(theaters):
        theater_showtimes = get_showtimes(theaters[i][1])
        for showtime in theater_showtimes:
            showtimes.append(showtime)
    
    for i, showtime in enumerate(showtimes):
        showtimes[i].ticket_data = get_ticket_data(showtimes[i].url)
        showtimes[i].seats = get_seat_data(showtimes[i].url)
        print(showtimes[i].title, showtimes[i].type, showtimes[i].time, showtimes[i].ticket_data, showtimes[i].seats)

main()

