import pandas as pd
import re

FILENAME = 'tourist_information_centre_along_80edays_route_USA & Canada'

df = pd.read_excel(f'{FILENAME}.xlsx') 

def extract_website(contact_info):
    contact_info = [str(info) for info in contact_info if pd.notna(info)]
    website_pattern = r'\b[\w-]+(\.[\w-]+)+\b'
    websites = [info for info in contact_info if isinstance(info, str) and re.search(website_pattern, info)]
    return websites[0] if websites else None

def extract_phone(contact_info):

    contact_info = [str(info) for info in contact_info if pd.notna(info)]
    phone_pattern = r'(\+?\d[\d\s-]{7,})'
    phones = [info for info in contact_info if isinstance(info, str) and re.search(phone_pattern, info)]
    return phones[0] if phones else None

def extract_emails(contact_info):
    contact_info = [str(info) for info in contact_info if pd.notna(info)]
    emails = re.findall(r'[\w\.-]+@[\w\.-]+', ', '.join(contact_info))
    return '; '.join(set(emails)) 

def extract_zip_country(address):
    if pd.notna(address):
    
        zip_code_match = re.search(r'\b\d{5}\b', address)
        zip_code = zip_code_match.group() if zip_code_match else None
        
    
        country_match = re.search(r'\b\w+$', address)
        country = country_match.group() if country_match else None
        
        return zip_code, country
    return None, None


df['Website'] = df.apply(lambda row: extract_website(row[2:]), axis=1)
df['Phone Number'] = df.apply(lambda row: extract_phone(row[2:].astype(str)), axis=1)
df['Emails'] = df.apply(lambda row: extract_emails(row[2:]), axis=1)
df[['Zip Code', 'Country']] = df.apply(lambda row: pd.Series(extract_zip_country(row['Address'])), axis=1)

df_clean = df[['Name', 'Address', 'Website', 'Phone Number', 'Emails', 'Zip Code', 'Country']].copy()
df_clean.columns = ['Name', 'Address', 'Website', 'Phone Number', 'Emails', 'Zip Code', 'Country']
df_clean.sort_values(by=['Zip Code'])


df_clean.to_excel(f'cleaned_{FILENAME}.xlsx', index=False)
