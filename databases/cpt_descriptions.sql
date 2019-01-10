create table cpt_descriptions as 
with short_desc as (
select
code, 
str as short_desc
from mrconso
where SAB = 'CPT' and tty='AB' ),
consumer_desc as (
select
code, 
str as consumer_desc
from mrconso
where SAB = 'CPT' and tty='ETCF'
),
clinician_desc as (
select
code, 
str as clinician_desc
from mrconso
where SAB = 'CPT' and tty='ETCLIN'
),
medium_descriptor as (
select
code, 
str as medium_desc
from mrconso
where SAB = 'CPT' and tty='SY'),
full_descriptor as (
select
code, 
str as full_desc
from mrconso
where SAB = 'CPT' and tty='PT'
)

SELECT 
sd.code,
short_desc,
consumer_desc,
clinician_desc,
medium_desc,
full_desc

from short_desc sd
    join consumer_desc cd on sd.code = cd.code
    join clinician_desc cl_d on sd.code = cl_d.code
    join medium_descriptor md on sd.code = md.code
    join full_descriptor fd on sd.code = fd.code
;
