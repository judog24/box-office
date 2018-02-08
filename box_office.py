import time
import datetime
import re
import argparse
import subprocess
import sqlite3
import bs4 as bs
from selenium import webdriver


conn = sqlite3.connect("D:\\box_office\\box_office.db")
c = conn.cursor()

def create_theaters_table():
    """
    Creates theaters table in sqlite3 database.

    One theater can only have one entry.

    theater_estimated_earnings is left null on insert and is updated after grabbing
    seat information for a screening.
    """
    c.execute("""CREATE TABLE IF NOT EXISTS theaters(
                     theater_id INTEGER, 
                     theater_name TEXT UNIQUE NOT NULL, 
                     theater_url INTEGER UNIQUE NOT NULL,
                     theater_estimated_earnings INTEGER, 
                     PRIMARY KEY(theater_id))""")

def create_movies_table():
    """
    Creates theaters table in sqlite3 database.

    One movie can only have one entry.  There may be instances of a 'duplicate' if a theater decides
    to alter the name of a movie to indicate that it is different than a traditional screening.

    movie_estimated_earnings is left null on insert and is updated after grabbing
    seat information for a screening.
    """
    c.execute("""CREATE TABLE IF NOT EXISTS movies(
                     movie_id INTEGER, 
                     movie_title TEXT UNIQUE NOT NULL, 
                     movie_estimated_earnings INTEGER,
                     PRIMARY KEY(movie_id))""")

def create_movie_locations_table():
    """
    Creates movie_locations table in sqlite3 database.

    This is an intermediary table for the many-to-many relationship between theaters and movies.
    This table stores all movies that have played at a theater.
    It is named movie_locations for semantic reasons.  Naming it movie_theaters would be confusing.

    estimated_earnings is left null on insert and is updated after grabbing seat information
    for a screening. estimated_earnings refers to how much a movie has made at specified theater.
    """
    c.execute("""CREATE TABLE IF NOT EXISTS movie_locations(
                     movie_location_id INTEGER, 
                     movie_id INTEGER, 
                     theater_id INTEGER, 
                     estimated_earnings INTEGER,
                     PRIMARY KEY(movie_location_id), 
                     FOREIGN KEY(movie_id) REFERENCES movies(movie_id), 
                     FOREIGN KEY(theater_id) REFERENCES theaters(theater_id))""")

def create_screenings_table():
    """
    Creates screenings table in sqlite3 database.

    screening_type refers to how a theater is showing a movie.  Standard, Cinemark XD, IMAX, 3D etc.

    screening_auditorium is left null on insert and is updated after grabbing ticket prices
    for a screening.

    screening_capacity, screening_seats_sold and screening_estimated_earnings are left null and are
    updated after retrieving seat data for a screening.
    """
    c.execute("""CREATE TABLE IF NOT EXISTS screenings(
                     screening_id INTEGER,
                     screening_url TEXT UNIQUE NOT NULL,
                     movie_location_id INTEGER,
                     screening_date TEXT,
                     screening_time TEXT,
                     screening_type TEXT,
                     reserved_seating TEXT,
                     screening_auditorium TEXT,
                     screening_capacity INTEGER,
                     screening_seats_sold INTEGER,
                     screening_estimated_earnings INTEGER,
                     PRIMARY KEY(screening_id),
                     FOREIGN KEY(movie_location_id) 
                        REFERENCES movie_locations(movie_location_id))""")

def create_tickets_table():
    """
    Creates tickets table in sqlite3 database.

    ticket_desc refers to the name of the type of ticket such as child/senior/matinee.

    Entries are added for every screening.  Doesn't this add many seemingly identical rows of data
    to the database?  Yes, but I went with this design to ensure that there is a historical
    list of prices since theaters like to change the prices of tickets.
    """
    c.execute("""CREATE TABLE IF NOT EXISTS tickets(
                     ticket_id INTEGER,
                     screening_id INTEGER,
                     ticket_desc TEXT,
                     ticket_price INTEGER,
                     PRIMARY KEY(ticket_id)
                     FOREIGN KEY(screening_id) REFERENCES screenings(screening_id))""")

def create_seats_table():
    """
    Creates seats table in sqlite3 database.

    This table holds seating information from screenings at theaters that have reserved seating.

    seat_location refers to the seat name such as G4 or F5.

    seat_type will most likely be 'standard'.  Other possible values can be 'wheelchair' and
    'companion' which refers to seats next to 'wheelchair' assigned spots.

    seat_status can be 'availableSeat', 'reservedSeat' or 'unavailableSeat'.
    The value 'unavailableSeat' appears when a seat in an auditorium exists but can't be reserved.
    I'm not exactly sure what the reasoning is on that, but so far I have only seen it occur with
    corner seats at the front row of an auditorium so it's probably a smart move on the
    theater's part.
    """
    c.execute("""CREATE TABLE IF NOT EXISTS seats(
                     seat_id INTEGER,
                     screening_id INTEGER,
                     seat_location TEXT,
                     seat_type TEXT,
                     seat_status TEXT,
                     primary key(seat_id),
                     FOREIGN KEY(screening_id) REFERENCES screenings(screening_id))""")

def create_tables():
    """
    Creates every table in sqlite3 database.
    """
    create_theaters_table()
    create_movies_table()
    create_movie_locations_table()
    create_screenings_table()
    create_tickets_table()
    create_seats_table()

def insert_theater(theater_name, theater_url):
    """
    Adds a theater to theaters table in sqlite3 database.  Duplicates not allowed.
    """
    try:
        with conn:
            c.execute("INSERT INTO theaters(theater_name, theater_url) VALUES (?, ?)",
                      (theater_name, theater_url))
    except sqlite3.IntegrityError:
        print('Could not add theater.  Theater: %s exists in database' % theater_name)

def insert_movie(movie_title):
    """
    Adds a movie to movies table in sqlite3 database.  Duplicates not allowed.
    """
    try:
        with conn:
            c.execute("INSERT INTO movies(movie_title) VALUES (?)",
                      (movie_title,))
    except sqlite3.IntegrityError:
        print('Could not add movie.  Movie: %s exists in database' % movie_title)

def insert_movie_location(movie_id, theater_id):
    """
    Only adds a movie playing at a theater if it has not been found in the database.
    """
    try:
        with conn:
            c.execute("""SELECT movie_location_id
                         FROM movie_locations
                         WHERE movie_id = ? AND theater_id = ?""",
                      (movie_id, theater_id))
            data = c.fetchone()
            if data is None:
                c.execute("INSERT INTO movie_locations(movie_id, theater_id) VALUES (?, ?)",
                          (movie_id, theater_id))
            else:
                print("Movie with id %s has already been added to this location" % movie_id)
    except sqlite3.IntegrityError:
        print("Could not add movie location")

def insert_screening(screening_url, movie_location_id, screening_date_time,
                     screening_type, reserved_seating):
    """
    Adds a screening to screenings table in sqlite3 database.

    screening_date_time is a list: [date, time]
    """
    try:
        with conn:
            c.execute("""INSERT INTO screenings(
                             screening_url, 
                             movie_location_id, 
                             screening_date, 
                             screening_time, 
                             screening_type, 
                             reserved_seating
                        ) VALUES (?,?,?,?,?,?)""",
                      (screening_url, movie_location_id, screening_date_time[0],
                       screening_date_time[1], screening_type, reserved_seating))
    except sqlite3.IntegrityError:
        print('Could not add screening for %s at %s' % (movie_location_id, screening_date_time[1]))

def insert_ticket(screening_id, ticket_desc, ticket_price):
    """
    Adds ticket data for a screening to tickets table in sqlite3 database.
    """
    try:
        with conn:
            c.execute("SELECT ticket_id FROM tickets WHERE screening_id = ? AND ticket_desc = ?",
                      (screening_id, ticket_desc))
            data = c.fetchone()
            if data is None:
                c.execute("""INSERT INTO tickets(screening_id, ticket_desc, ticket_price)
                             VALUES (?,?,?)""",
                          (screening_id, ticket_desc, ticket_price))
            else:
                print("Ticket data has already been added for screening: %s" % screening_id)
    except sqlite3.IntegrityError:
        print("Error inserting ticket data")

def insert_seat(screening_id, seat_location, seat_type, seat_status):
    """
    Adds seat data for a screening to seats table in sqlite3 database.
    """
    try:
        with conn:
            c.execute("SELECT seat_id FROM seats WHERE screening_id = ? AND seat_location = ?",
                      (screening_id, seat_location))
            data = c.fetchone()
            if data is None:
                c.execute("""INSERT INTO seats(screening_id, seat_location, seat_type, seat_status)
                             VALUES (?,?,?,?)""",
                          (screening_id, seat_location, seat_type, seat_status))
            else:
                print("Seat: %s has already been added for this screening" % seat_location)
    except sqlite3.IntegrityError:
        print("Error inserting seat")

def from_db_get_theater_id(theater_url):
    """
    Returns the theater_id from theaters table using a theater's url.
    """
    try:
        with conn:
            c.execute("SELECT theater_id FROM theaters WHERE theater_url = ?", (theater_url,))
            return c.fetchone()[0]
    except sqlite3.IntegrityError:
        print("Error retrieving theater_id")

def from_db_get_screening_id(screening_url):
    """
    Returns screening_id from screening table using a screening's url.
    """
    try:
        with conn:
            c.execute("""SELECT screening_id FROM screenings
                         WHERE screening_url = ?""", (screening_url,))
            return c.fetchone()[0]
    except sqlite3.IntegrityError:
        print("Error retrieving screening_id")

def from_db_get_theater_urls():
    """
    Returns theater_urls from theaters table.
    """
    try:
        with conn:
            c.execute("SELECT theater_url FROM theaters")
            return c.fetchall()
    except sqlite3.IntegrityError:
        print("Could not retrieve theater URLs from database")

def from_db_get_movie_id(movie_title):
    """
    Returns movie_id from movies table using a movie's title.
    """
    try:
        with conn:
            c.execute("SELECT movie_id FROM movies WHERE movie_title = ?", (movie_title,))
            return c.fetchone()[0]
    except sqlite3.IntegrityError:
        print("Error retrieving movie_id")

def from_db_get_movie_location_id(movie_id, theater_id):
    """
    Returns movie_location_id from movie_locations table using a movie's id and a theater's id
    """
    try:
        with conn:
            c.execute("""SELECT movie_location_id FROM movie_locations
                         WHERE movie_id = ? AND theater_id = ?""",
                      (movie_id, theater_id))
            return c.fetchone()[0]
    except sqlite3.IntegrityError:
        print("Error retrieving movie_location_id")

def from_db_get_daily_screenings(today):
    """
    Returns all showtimes scheduled for today at every theater.
    """
    try:
        with conn:
            c.execute("SELECT screening_id, screening_url FROM screenings WHERE screening_date = ?",
                      (today,))
            return c.fetchall()
    except sqlite3.IntegrityError:
        print("Error retrieving screenings")

def from_db_get_daily_reserved(today):
    """
    Returns all showtimes with reserved seating for today at every theater.
    """
    try:
        with conn:
            c.execute("""SELECT screening_id, screening_url, screening_time
                         FROM screenings WHERE screening_date = ? AND reserved_seating = 'True'
                         ORDER BY screening_time ASC""",
                      (today,))
            return c.fetchall()
    except sqlite3.IntegrityError:
        print("Error retrieving screenings")

def update_screening_auditorium(screening_id, screening_auditorium):
    """
    Updates screening_auditorium column in screenings table for a given screening.
    """
    try:
        with conn:
            c.execute("UPDATE screenings SET screening_auditorium = ? WHERE screening_id = ?",
                      (screening_auditorium, screening_id))
    except sqlite3.IntegrityError:
        print("Could not update auditorium in screening")

def update_screening_capacity_sold(screening_id):
    """
    Updates screening_capacity, screening_seats_sold and screening_estimated_earnings columns
    from screenings table for a given screening.
    """
    try:
        with conn:
            c.execute("""SELECT count(*) FROM seats
                         WHERE screening_id = ? AND NOT seat_status = 'unavailableSeat'""",
                      (screening_id,))
            screening_capacity = c.fetchone()[0]

            c.execute("""SELECT count(*) FROM seats
                         WHERE screening_id = ? AND seat_status='reservedSeat'""",
                      (screening_id,))
            screening_seats_sold = c.fetchone()[0]

            c.execute("""SELECT ticket_price FROM tickets
                         WHERE screening_id = ? ORDER BY ticket_price DESC""",
                      (screening_id,))
            ticket_price = c.fetchone()[0]

            screening_estimated_earnings = screening_seats_sold*ticket_price

            c.execute("""UPDATE screenings
                         SET screening_capacity = ?,
                             screening_seats_sold = ?,
                             screening_estimated_earnings = ?
                        WHERE screening_id = ?""",
                      (screening_capacity, screening_seats_sold, screening_estimated_earnings,
                       screening_id))
    except sqlite3.IntegrityError:
        print("Could not update seat information in screening")

def update_movie_location_earnings(screening_id):
    """
    Updates estimated earnings for a movie at a specified theater.
    """
    try:
        with conn:
            c.execute("SELECT movie_location_id FROM screenings WHERE screening_id = ?",
                      (screening_id,))
            movie_location_id = c.fetchone()[0]
            c.execute("""SELECT SUM(screening_estimated_earnings) FROM screenings
                         WHERE movie_location_id = ?""",
                      (movie_location_id,))
            movie_location_earnings = c.fetchone()[0]
            c.execute("""UPDATE movie_locations SET estimated_earnings = ?
                         WHERE movie_location_id = ?""",
                      (movie_location_earnings, movie_location_id))
    except sqlite3.IntegrityError:
        print("Could not update earnings for movie at this theater")

def update_movie_earnings(screening_id):
    """
    Updates estimated earnings for a movie from all theaters.
    """
    try:
        with conn:
            c.execute("""SELECT movie_locations.movie_id FROM screenings
                         INNER JOIN movie_locations
                         ON movie_locations.movie_location_id = screenings.movie_location_id
                         AND screening_id = ?""",
                      (screening_id,))
            movie_id = c.fetchone()[0]
            c.execute("SELECT SUM(estimated_earnings) FROM movie_locations WHERE movie_id = ?",
                      (movie_id,))
            movie_earnings = c.fetchone()[0]

            c.execute("UPDATE movies SET movie_estimated_earnings = ? WHERE movie_id = ?",
                      (movie_earnings, movie_id))
    except sqlite3.IntegrityError:
        print("Could not update earnings for movie")

def update_theater_earnings(screening_id):
    """
    Updates estimated earnings for a theater with a sum of all earnings from movies playing
    at specified theater.
    """
    try:
        with conn:
            c.execute("""SELECT movie_locations.theater_id FROM screenings
                         INNER JOIN movie_locations
                         ON movie_locations.movie_location_id = screenings.movie_location_id
                         AND screening_id = ?""",
                      (screening_id,))
            theater_id = c.fetchone()[0]
            c.execute("SELECT SUM(estimated_earnings) FROM movie_locations WHERE theater_id = ?",
                      (theater_id,))
            movie_earnings = c.fetchone()[0]

            c.execute("UPDATE theaters SET theater_estimated_earnings = ? WHERE theater_id = ?",
                      (movie_earnings, theater_id))
    except sqlite3.IntegrityError:
        print("Could not update earnings for theater")

def update_earnings(screening_id):
    """
    Updates earnings totals for a screening, movie at a theater, movie and theter.

    Runs after getting seat data for a screening.
    """
    update_screening_capacity_sold(screening_id)
    update_movie_location_earnings(screening_id)
    update_movie_earnings(screening_id)
    update_theater_earnings(screening_id)

def open_browser(url):
    """
    Waits 3 seconds for page to load before performing actions
    """
    browser = webdriver.Firefox()
    browser.get(url)
    time.sleep(3)
    return browser

def get_time_date(showtime_url):
    """
    Returns two strings.  A date formatted as YYYY-MM-DD and time using 24-hour clock.
    """
    date_time = re.findall(r'date=(.*?)&', showtime_url)
    date, time = date_time[0].split('+')
    return date, time

def get_amenity(showtime_type):
    """
    Returns the screening format of a movie and whether or not there is reserved seating.

    <a data-amenity-name="Reserved seating"></a>
    Function only gets called when a screening has reserved seating.
    """
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
    elif showtime_type.find('a', {'data-amenity-name': 'The Met Opera'}):
        show_type = 'The Met Opera'
    else:
        show_type = 'Standard'

    if showtime_type.find('a', {'data-amenity-name': 'Reserved seating'}):
        reserved_seating = 'True'
    else:
        reserved_seating = 'False'

    return show_type, reserved_seating

def movies(theater_url):
    """
    Yields the title of all movies playing at a theater.

    Loops through <li> elements with the following general structure:
    
    <li class="fd-movie">
        <div class="fd-movie__details">
            <a class="dark">Movie Name</a>
        </div>
    </li>
    """
    browser = open_browser(theater_url)
    soup = bs.BeautifulSoup(browser.page_source, 'lxml')

    movies_soup = soup.find_all('li', {'class': 'fd-movie'})

    for movie in movies_soup:
        yield movie.find('a', {'class': 'dark'}).text

    browser.quit()

def get_movies(theater_url):
    """
    Calls functions to find movies playing at a theater and add them to database.
    """
    theater_id = from_db_get_theater_id(theater_url)
    for movie in movies(theater_url):
        insert_movie(movie)
        movie_id = from_db_get_movie_id(movie)
        insert_movie_location(movie_id, theater_id)

def showtimes(theater_url):
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
    browser = open_browser(theater_url)
    soup = bs.BeautifulSoup(browser.page_source, 'lxml')

    movies_soup = soup.find_all('li', {'class': 'fd-movie'})

    for movie in movies_soup:
        title = movie.find('a', {'class': 'dark'}).text
        movie_id = from_db_get_movie_id(title)
        variants = movie.find_all('li', {'class': 'fd-movie__showtimes-variant'})

        for variant in variants:
            screening_type, reserved_seating = get_amenity(variant)
            screenings = variant.find_all('a', {'class': 'showtime-btn--available'})

            for screening in screenings:
                yield screening['href'], movie_id, screening_type, reserved_seating
    browser.quit()

def get_showtimes(theater_url):
    """
    Calls functions to find showtimes for each movie at a theater and add showtime data to database.
    """
    theater_id = from_db_get_theater_id(theater_url)
    for showtime in showtimes(theater_url):
        screening_date, screening_time = get_time_date(showtime[0])
        movie_location_id = from_db_get_movie_location_id(showtime[1], theater_id)
        screening_date_time = [screening_date, screening_time]
        insert_screening(showtime[0], movie_location_id, screening_date_time,
                         showtime[2], showtime[3])

def ticket_prices(screening_url):
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
    browser = open_browser(screening_url)
    soup = bs.BeautifulSoup(browser.page_source, 'lxml')
    error = soup.find('section', {'class': 'errorMessages'})
    

    if error:
        error_message = soup.find('div', {'class': 'errorHeaderMessage'}).text
        browser.quit()
        yield error_message
    else:
        #auditorium = soup.find('h2', {'id': 'auditoriumInfo'}).text
        auditorium = soup.find('h2', {'id': 'auditoriumInfo'})
        tickets_table = soup.find('table', {'class': 'quantityTable'})
        tickets_rows = tickets_table.find_all('tr')
        if auditorium is not None:   
            for ticket_row in tickets_rows:
                ticket_type = ticket_row.find('input', {'name': 'pricedesc'})
                price = ticket_row.find('input', {'name': 'price'})
                yield ticket_type['value'], price['value'], auditorium.text
            browser.quit()
        else:
            for ticket_row in tickets_rows:
                ticket_type = ticket_row.find('input', {'name': 'pricedesc'})
                price = ticket_row.find('input', {'name': 'price'})
                yield ticket_type['value'], price['value'], auditorium
            browser.quit()

def get_ticket_prices(today):
    """
    Calls functions to get ticket prices and auditorium for each screening today.
    """
    showtimes_today = from_db_get_daily_screenings(today)
    e1 = '\n        This showtime is no longer available. Please select a different showtime.\n        '

    for showtime in showtimes_today:
        screening_id = showtime[0]
        for ticket_price in ticket_prices(showtime[1]):
            if ticket_price == e1:
                print('This showtime is no longer available')
                auditorium = None
            else:           
                insert_ticket(screening_id, ticket_price[0], ticket_price[1])
                auditorium = ticket_price[2]
        if auditorium is not None:
            update_screening_auditorium(screening_id, auditorium)

def seats(screening_url):
    """
    Seating chart has the following general strucutre:

    <div id="svg-Layer_1">
        <div id="H16" class="standard availableSeat" data-seats="H16--0"></div>
        <div id="F7" class="standard reservedSeat"></div>
        <div id="D8" class="companion availableSeat"></div>
        <div class="wheelchair availableSeat" id="D11" data-seats="D11-58"></div>
    </div>
    """
    browser = open_browser(screening_url)
    select_option = '//*[@id="AreaRepeater_TicketRepeater_0_quantityddl_0"]/option[2]'
    browser.find_element_by_xpath(select_option).click()
    browser.find_element_by_xpath('//*[@id="NewCustomerCheckoutButton"]').click()
    soup = bs.BeautifulSoup(browser.page_source, 'lxml')
    seat_chart = soup.find('div', {'id': 'svg-Layer_1'})
    seats_screening = seat_chart.find_all('div')
    for seat in seats_screening:
        #('H16', ['standard', 'availableSeat'], 'Auditorium 9')
        yield seat['id'], seat['class']
    browser.quit()

def get_seat_data(screening_url):
    """
    Gathers seat data for a screening and updates earnings totals.
    """
    screening_id = from_db_get_screening_id(screening_url)
    for seat in seats(screening_url):
        if len(seat[1]) > 1:
            insert_seat(screening_id, seat[0], seat[1][0], seat[1][1])
        else: #If seat is not available
            insert_seat(screening_id, seat[0], seat[1][0], seat[1][0])
        update_earnings(screening_id)

def verify_showtime(seen, showtime):
    """
    Ensures that scheduled tasks do not start at the same time.
    """
    if showtime not in seen:
        return showtime
    else:
        adjusted_time = showtime - datetime.timedelta(minutes=1)
        return verify_showtime(seen, adjusted_time)

def schedule_task(showtime_id, showtime_url, stime):
    """
    Schedules script to run using Schtasks in Windows PowerShell.
    """
    task_time = stime.replace(':', '-')
    tname = 'scrn ' + str(showtime_id) + ' at ' + task_time
    script_location = "D:\\box_office\\box_office.py"
    trun = "cd D:\\box_office; PowerShell python %s -seats '%s' -st" % (script_location, showtime_url)
    task = """cd D:\\box_office; schtasks /create /tn "%s" /sc once /st %s /tr "%s" /f """ % (tname, stime, trun)
    print(task)
    
    subprocess.call("""%s""" % task)
    print('Created task: ', tname)

def queue_times(today):
    """
    Gathers all showtimes with reserved seating and schedules script to run
    3 minutes before each screening starts.
    """
    showtimes_today = from_db_get_daily_reserved(today)
    seen = set()

    for showtime in showtimes_today:
        showtime_start = showtime[2]
        show_date = datetime.datetime.strptime('%s %s' % (today, showtime_start), '%Y-%m-%d %H:%M')
        time_checkseats = show_date - datetime.timedelta(minutes=3)
        verified_time = verify_showtime(seen, time_checkseats)
        seen.add(verified_time)
        verified_time_string = verified_time.strftime('%H:%M')
        schedule_task(showtime[0], showtime[1], verified_time_string)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-st', action='store_true', required=True)

    #One theater required in database for other options to work
    parser.add_argument('-insert_theater_name', type=str,
                        help='Name of new theater to track.  Also requires -u for theater url')
    parser.add_argument('-url_theater', type=str, help='URL of new theater to track.  Requires -i')

    parser.add_argument('-auto', action='store_true',
                        help='Run to all theater info and schedule seat checks.')

    parser.add_argument('-movies', action='store_true',
                        help='Gathers movies playing at each theater today')
    parser.add_argument('-showtimes', action='store_true',
                        help='Gathers showtimes of each movie at every theater today')
    parser.add_argument('-tickets', action='store_true',
                        help='Gathers ticket prices for each showtime today')
    parser.add_argument('-enque', action='store_true')

    parser.add_argument('-seats', type=str,
                        help='Gathers seat information for a showtime with a screening url.')
    args = parser.parse_args()

    if args.st:
        create_tables()
        today = datetime.date.today()
        today_string = today.isoformat()
        theater_urls = from_db_get_theater_urls()

    if args.seats:
        get_seat_data(args.seats)
    elif args.auto:
        for theater_url in theater_urls:
            get_movies(theater_url[0])
            get_showtimes(theater_url[0])
            
        get_ticket_prices(today_string)    
        queue_times(today_string)
    elif args.insert_theater_name:
        if args.url_theater:
            insert_theater(args.insert_theater_name, args.url_theater)
        else:
            print("Theater URL is required")
    elif args.enque:
        print('adding schedule')
        queue_times(today_string)
    elif args.movies:
        for theater_url in theater_urls:
            get_movies(theater_url[0])
    elif args.showtimes:
        for theater_url in theater_urls:
            get_showtimes(theater_url[0])
    elif args.tickets:
        get_ticket_prices(today_string)

if __name__ == '__main__':
    main()