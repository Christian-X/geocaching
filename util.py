#!/usr/bin/python3
import sys


#0 - 65535               GC0 - GCFFFF (Hexadecimal, 4 digits)
#65536 - 512400          GCG000 - GCZZZZ (base31, 4 digits)
#512401 - 28218031       GC10000 - GCZZZZZ (base31, 5 digits)
alphabet="0123456789ABCDEFGHJKMNPQRTVWXYZ"
CACHE_CODE_BASE31_MAGIC_NUMBER = 411120
def base31Decode(input):
    input=input.upper()
    result=0
    for c in input:
        result=result*31
        result=result+alphabet.index(alphabet,c)
    return result

def base31Encode(value):
    base=31
    result=""
    while value>0:
        result=alphabet[int(value%base)]+result
        value=int(value/base)
    return result    
    

def toGCCode(value):
    if value==None:
        return None
    if value<65536:
        return "%x"%(value,)
    return base31Encode(CACHE_CODE_BASE31_MAGIC_NUMBER+value)
        
