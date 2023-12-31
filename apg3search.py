# *************************************
# * Ash Pattern Generator (apgsearch) *
# *************************************
# * Version: v1.1  (beta release)     *
# *                                   *
# *       All times in UTC+0          *
# *                                   *
# *          ALPHA RELEASES           *
# *                                   *
# * Apgs3arch version 0 by "lk050807" *
# * Apgs3arch version 0.0.1 by "dvgrn"*
# * on 4:03 PM, Dec 17, 2023          *
# * Apgs3arch version 0.0.2 by "very" *
# * on 2:20 AM, Dec 18, 2023          *
# *Apgs3arch version 0.0.3 by lk050807*
# * on 9:25 PM, Dec 18, 2023          *
# *************************************
#
# -- Processes roughly 100 soups per (second . core . GHz), using caching
#    and machine-learning to optimise itself during runtime.
#
# -- Can perfectly identify oscillators with period < 1000, well-separated
#    spaceships of low period, and certain infinite-growth patterns (such
#    guns and puffers, including both naturally-occurring types of switch
#    engine).
#
# -- Separates most pseudo-objects into their constituent parts, including
#    all pseudo-still-lifes of 18 or fewer live cells (which is the maximum
#    theoretically possible, given there is a 19-cell pseudo-still-life
#    with two distinct decompositions).
#
# -- Correctly separates non-interacting standard spaceships, irrespective
#    of their proximity. In particular, a LWSS-on-LWSS is registered as two
#    LWSSes, whereas an LWSS-on-HWSS is registered as a single spaceship
#    (since they interact by suppressing sparks).
#
# -- At least 99.9999999999% reliable at identifying objects in asymmetrical
#    soups in B3/S23 (based on the fact that out of over 10^12 objects that
#    have appeared, there are no errors).
#
# -- Scores soups based on the total excitement of the ash objects.
#
# -- Support for other outer-totalistic rules, including detection and
#    classification of various types of infinite growth.
#
# -- Support for symmetrical soups.
#
# -- Uploads results to the server at http://https://catagolue.hatsya.com/ (which
#    currently has collected over 2.7 * 10^12 objects).
#
# -- Peer-reviews others' contributions to ensure data integrity for the
#    asymmetrical B3/S23 census.
#
# By Adam P. Goucher, with contributions from Andrew Trevorrow, Tom Rokicki,
# Nathaniel Johnston, Dave Greene and Richard Schank.
# Converted by "lk050807"(Kevin Lin)

'''
Copyright 2015 Adam P. Goucher

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''

import golly as g
from glife import rect, pattern
import time
import math
import operator
import hashlib
import datetime
import os
import urllib.request, urllib.error, urllib.parse

def get_server_address():
    # Should be 'http://https://catagolue.hatsya.com/' for the released version,
    # and 'http://localhost:8080' for the development version:    
    return 'http://catagolue.hatsya.com'
    # return 'http://localhost:8080'


# Engages with Catagolue's authentication system ('payment over SHA-256',
# affectionately abbreviated to 'payosha256'):
#
# The payosha256_key can be obtained from logging into Catagolue in your
# web browser and visiting http://https://catagolue.hatsya.com//payosha256
def authenticate(payosha256_key, operation_name):

    g.show("Authenticating with Catagolue via the payosha256 protocol...")

    payload = "payosha256:get_token:"+payosha256_key+":"+operation_name

    req = urllib.request.Request(get_server_address() + "/payosha256", payload, {"Content-type": "text/plain"})
    f = urllib.request.urlopen(req)

    if (f.getcode() != 200):
        return None

    resp = f.read()

    lines = resp.splitlines()

    for line in lines:
        parts = line.split(':')

        if (len(parts) < 3):
            continue

        if (parts[1] != 'good'):
            continue

        target = parts[2]
        token = parts[3]

        g.show("Token " + token + " obtained from payosha256. Performing proof of work with target " + target + "...")

        for nonce in range(100000000):

            prehash = token + ":" + str(nonce)
            posthash = hashlib.sha256(prehash.encode('utf8')).hexdigest()

            if (posthash < target):
                break

        if (posthash > target):
            continue

        g.show("String "+prehash+" is sufficiently valuable ("+posthash+" < "+target+").")

        payload = "payosha256:pay_token:"+prehash+"\n"

        return payload

    return None

# Sends the results to Catagolue:
def catagolue_results(results, payosha256_key, operation_name, endpoint="/apgsearch", return_point=None):

    try:

        payload = authenticate(payosha256_key, operation_name)

        if payload is None:
            return 1

        payload += results

        req = urllib.request.Request(get_server_address() + endpoint, payload, {"Content-type": "text/plain"})

        f = urllib.request.urlopen(req)

        if (f.getcode() != 200):
            return 2

        resp = f.read()

        try:
            f2 = open(g.getdir("data")+"catagolue-response.txt", 'w')
            f2.write(resp)
            f2.close()

            if return_point is not None:
                return_point[0] = resp
            
        except:
            g.warn("Unable to save catagolue response file.")

        return 0

    except:

        return 1

# Takes approximately 350 microseconds to construct a 16-by-16 soup based
# on a SHA-256 cryptographic hash in the obvious way.
def hashsoup(instring, sym):

    s = hashlib.sha256(instring.encode('utf8')).digest()

    thesoup = []

    if sym in ['D2_x', 'D8_1', 'D8_4']:
        d = 1
    elif sym in ['D4_x1', 'D4_x4']:
        d = 2
    else:
        d = 0

    for j in range(32):

        t = int(s[j])

        for k in range(8):

            if (sym == '8x32'):
                x = k + 8*(j % 4)
                y = int(j / 4)
            else:
                x = k + 8*(j % 2)
                y = int(j / 2)

            if (t & (1 << (7 - k))):

                if ((d == 0) | (x >= y)):

                    thesoup.append(x)
                    thesoup.append(y)

                elif (sym == 'D4_x1'):

                    thesoup.append(y)
                    thesoup.append(-x)

                elif (sym == 'D4_x4'):

                    thesoup.append(y)
                    thesoup.append(-x-1)

                if ((sym == 'D4_x1') & (x == y)):

                    thesoup.append(y)
                    thesoup.append(-x)

                if ((sym == 'D4_x4') & (x == y)):

                    thesoup.append(y)
                    thesoup.append(-x-1)

    # Checks for diagonal symmetries:
    if (d >= 1):
        for x in range(0, len(thesoup), 2):
            thesoup.append(thesoup[x+1])
            thesoup.append(thesoup[x])
        if d == 2:
            if (sym == 'D4_x1'):
                for x in range(0, len(thesoup), 2):
                    thesoup.append(-thesoup[x+1])
                    thesoup.append(-thesoup[x])
            else:
                for x in range(0, len(thesoup), 2):
                    thesoup.append(-thesoup[x+1] - 1)
                    thesoup.append(-thesoup[x] - 1)
            return thesoup

    # Checks for orthogonal x symmetry:
    if sym in ['D2_+1', 'D4_+1', 'D4_+2']:
        for x in range(0, len(thesoup), 2):
            thesoup.append(thesoup[x])
            thesoup.append(-thesoup[x+1])
    elif sym in ['D2_+2', 'D4_+4']:
        for x in range(0, len(thesoup), 2):
            thesoup.append(thesoup[x])
            thesoup.append(-thesoup[x+1] - 1)

    # Checks for orthogonal y symmetry:
    if sym in ['D4_+1']:
        for x in range(0, len(thesoup), 2):
            thesoup.append(-thesoup[x])
            thesoup.append(thesoup[x+1])
    elif sym in ['D4_+2', 'D4_+4']:
        for x in range(0, len(thesoup), 2):
            thesoup.append(-thesoup[x] - 1)
            thesoup.append(thesoup[x+1])

    # Checks for rotate2 symmetry:
    if sym in ['C2_1', 'C4_1', 'D8_1']:
        for x in range(0, len(thesoup), 2):
            thesoup.append(-thesoup[x])
            thesoup.append(-thesoup[x+1])
    elif sym in ['C2_2']:
        for x in range(0, len(thesoup), 2):
            thesoup.append(-thesoup[x])
            thesoup.append(-thesoup[x+1]-1)
    elif sym in ['C2_4', 'C4_4', 'D8_4']:
        for x in range(0, len(thesoup), 2):
            thesoup.append(-thesoup[x]-1)
            thesoup.append(-thesoup[x+1]-1)

    # Checks for rotate4 symmetry:
    if (sym in ['C4_1', 'D8_1']):
        for x in range(0, len(thesoup), 2):
            thesoup.append(thesoup[x+1])
            thesoup.append(-thesoup[x])
    elif (sym in ['C4_4', 'D8_4']):
        for x in range(0, len(thesoup), 2):
            thesoup.append(thesoup[x+1])
            thesoup.append(-thesoup[x]-1)

    return thesoup


# Obtains a canonical representation of any oscillator/spaceship that (in
# some phase) fits within a 40-by-40 bounding box. This representation is
# alphanumeric and lowercase, and so much more compact than RLE. Compare:
#
# Common name: pentadecathlon
# Canonical representation: 4r4z4r4
# Equivalent RLE: 2bo4bo$2ob4ob2o$2bo4bo!
#
# It is a generalisation of a notation created by Allan Weschler in 1992.
def canonise(duration):

    representation = "#"

    # We need to compare each phase to find the one with the smallest
    # description:
    for t in range(duration):

        rect = g.getrect()
        if (len(rect) == 0):
            return "0"

        if ((rect[2] <= 40) & (rect[3] <= 40)):
            # Fits within a 40-by-40 bounding box, so eligible to be canonised.
            # Choose the orientation which results in the smallest description:
            representation = compare_representations(representation, canonise_orientation(rect[2], rect[3], rect[0], rect[1], 1, 0, 0, 1))
            representation = compare_representations(representation, canonise_orientation(rect[2], rect[3], rect[0]+rect[2]-1, rect[1], -1, 0, 0, 1))
            representation = compare_representations(representation, canonise_orientation(rect[2], rect[3], rect[0], rect[1]+rect[3]-1, 1, 0, 0, -1))
            representation = compare_representations(representation, canonise_orientation(rect[2], rect[3], rect[0]+rect[2]-1, rect[1]+rect[3]-1, -1, 0, 0, -1))
            representation = compare_representations(representation, canonise_orientation(rect[3], rect[2], rect[0], rect[1], 0, 1, 1, 0))
            representation = compare_representations(representation, canonise_orientation(rect[3], rect[2], rect[0]+rect[2]-1, rect[1], 0, -1, 1, 0))
            representation = compare_representations(representation, canonise_orientation(rect[3], rect[2], rect[0], rect[1]+rect[3]-1, 0, 1, -1, 0))
            representation = compare_representations(representation, canonise_orientation(rect[3], rect[2], rect[0]+rect[2]-1, rect[1]+rect[3]-1, 0, -1, -1, 0))

        g.run(1)

    return representation

# A subroutine used by canonise:
def canonise_orientation(length, breadth, ox, oy, a, b, c, d):

    representation = ""

    chars = "0123456789abcdefghijklmnopqrstuvwxyz"

    for v in range(int((breadth-1)/5)+1):
        zeroes = 0
        if (v != 0):
            representation += "z"
        for u in range(length):
            baudot = 0
            for w in range(5):
                x = ox + a*u + b*(5*v + w)
                y = oy + c*u + d*(5*v + w)
                baudot = (baudot >> 1) + 16*g.getcell(x, y)
            if (baudot == 0):
                zeroes += 1
            else:
                if (zeroes > 0):
                    if (zeroes == 1):
                        representation += "0"
                    elif (zeroes == 2):
                        representation += "w"
                    elif (zeroes == 3):
                        representation += "x"
                    else:
                        representation += "y"
                        representation += chars[zeroes - 4]
                zeroes = 0
                representation += chars[baudot]
    return representation

# Compares strings first by length, then by lexicographical ordering.
# A hash character is worse than anything else.
def compare_representations(a, b):

    if (a == "#"):
        return b
    elif (b == "#"):
        return a
    elif (len(a) < len(b)):
        return a
    elif (len(b) < len(a)):
        return b
    elif (a < b):
        return a
    else:
        return b

# Finds the gradient of the least-squares regression line corresponding
# to a list of ordered pairs:
def regress(pairlist):

    cumx = 0.0
    cumy = 0.0
    cumvar = 0.0
    cumcov = 0.0

    for x,y in pairlist:

        cumx += x
        cumy += y

    cumx = cumx / len(pairlist)
    cumy = cumy / len(pairlist)

    for x,y in pairlist:

        cumvar += (x - cumx)*(x - cumx)
        cumcov += (x - cumx)*(y - cumy)

    return (cumcov / cumvar)

# Analyses a pattern whose average population follows a power-law:
def powerlyse(stepsize, numsteps):

    g.setalgo("HashLife")
    g.setbase(2)
    g.setstep(stepsize)

    poplist = [0]*numsteps

    poplist[0] = int(g.getpop())

    pointlist = []

    for i in range(1, numsteps, 1):

        g.step()
        poplist[i] = int(g.getpop()) + poplist[i-1]

        if (i % 50 == 0):

            g.fit()
            g.update()

        if (i > numsteps//2):

            pointlist.append((math.log(i),math.log(poplist[i]+1.0)))

    power = regress(pointlist)

    if (power < 1.10):
        return "unidentified"
    elif (power < 1.65):
        return "zz_REPLICATOR"
    elif (power < 2.05):
        return "zz_LINEAR"
    elif (power < 2.8):
        return "zz_EXPLOSIVE"
    else:
        return "zz_QUADRATIC"

# Gets the period of an interleaving of degree-d polynomials:
def deepperiod(sequence, maxperiod, degree):

    for p in range(1, maxperiod, 1):

        good = True

        for i in range(maxperiod):

            diffs = [0] * (degree + 2)
            for j in range(degree + 2):

                diffs[j] = sequence[i + j*p]

            # Produce successive differences:
            for j in range(degree + 1):
                for k in range(degree + 1):
                    diffs[k] = diffs[k] - diffs[k + 1]

            if (diffs[0] != 0):
                good = False
                break

        if (good):
            return p
    return -1

# Analyses a linear-growth pattern, returning a hash:
def linearlyse(maxperiod):

    poplist = [0]*(3*maxperiod)

    for i in range(3*maxperiod):

        g.run(1)
        poplist[i] = int(g.getpop())

    p = deepperiod(poplist, maxperiod, 1)

    if (p == -1):
        return "unidentified"

    difflist = [0]*(2*maxperiod)

    for i in range(2*maxperiod):

        difflist[i] = poplist[i + p] - poplist[i]

    q = deepperiod(difflist, maxperiod, 0)

    moments = [0, 0, 0]

    for i in range(p):

        moments[0] += (poplist[i + q] - poplist[i])
        moments[1] += (poplist[i + q] - poplist[i]) ** 2
        moments[2] += (poplist[i + q] - poplist[i]) ** 3

    prehash = str(moments[1]) + "#" + str(moments[2])

    # Linear-growth patterns with growth rate zero are clearly errors!
    if (moments[0] == 0):
        return "unidentified"

    return "yl" + str(p) + "_" + str(q) + "_" + str(moments[0]) + "_" + hashlib.md5(prehash.encode('utf8')).hexdigest()

    
# This explodes pseudo-still-lifes and pseudo-oscillators into their
# constituent parts.
#
# -- Requires the period (if oscillatory) and graph-theoretic diameter
#    to not exceed 4096.
# -- Never mistakenly separates a true object.
# -- Correctly separates most pseudo-still-lifes, including the famous:
#    http://www.conwaylife.com/wiki/Quad_pseudo_still_life
# -- Works perfectly for all still-lifes of up to 17 bits.
# -- Doesn't separate 'locks', of which the smallest example has 18
#    bits and is unique:
#
#     ** **
#     ** **
#
#    * *** *
#    ** * **
#
# To use this function (standalone), merely copy it into a script of
# the following form:
#
#   import golly as g
#
#   def pseudo_bangbang():
#
#   [...]
#
#   pseudo_bangbang()
#
# and execute it in Golly with a B3/S23 universe containing any still-
# lifes or oscillators you want to separate. Pure objects correspond to
# connected components in the final state of the universe.
#
# This has dependencies on the rules ContagiousLife, PercolateInfection
# and EradicateInfection.
#
# Not to be confused with the Unix shell instruction for repeating the
# previous instruction as a superuser (sudo !!), or indeed with any
# parodies of this song: https://www.youtube.com/watch?v=YswhUHH6Ufc
#
# Adam P. Goucher, 2014-08-25
def pseudo_bangbang(alpharule):

    g.setrule("APG_ContagiousLife_" + alpharule)
    g.setbase(2)
    g.setstep(12)
    g.step()

    celllist = g.getcells(g.getrect())

    for i in range(0, len(celllist)-1, 3):
        
        # Only infect cells that haven't yet been infected:
        if (g.getcell(celllist[i], celllist[i+1]) <= 2):

            # Seed an initial 'infected' (red) cell:
            g.setcell(celllist[i], celllist[i+1], g.getcell(celllist[i], celllist[i+1]) + 2)

            prevpop = 0
            currpop = int(g.getpop())

            # Continue infecting until the entire component has been engulfed:
            while (prevpop != currpop):

                # Percolate the infection to every cell in the island:
                g.setrule("APG_PercolateInfection")
                g.setbase(2)
                g.setstep(12)
                g.step()

                # Transmit the infection across any bridges.
                g.setrule("APG_ContagiousLife_" + alpharule)
                g.setbase(2)
                g.setstep(12)
                g.step()

                prevpop = currpop
                currpop = int(g.getpop())
                
            g.fit()
            g.update()

            # Red becomes green:
            g.setrule("APG_EradicateInfection")
            g.step()


# Counts the number of live cells of each degree:
def degreecount():

    celllist = g.getcells(g.getrect())
    counts = [0,0,0,0,0,0,0,0,0]

    for i in range(0, len(celllist), 2):

        x = celllist[i]
        y = celllist[i+1]

        degree = -1

        for ux in range(x - 1, x + 2):
            for uy in range(y - 1, y + 2):

                degree += g.getcell(ux, uy)

        counts[degree] += 1

    return counts

# Counts the number of live cells of each degree in generations 1 and 2:
def degreecount2():

    g.run(1)
    a = degreecount()
    g.run(1)
    b = degreecount()

    return (a + b)

# If the universe consists only of disjoint *WSSes, this will return
# a triple (l, w, h) giving the quantities of each *WSS. Otherwise,
# this function will return (-1, -1, -1).
#
# This should only be used to separate period-4 moving objects which
# may contain multiple *WSSes.
def countxwsses():

    degcount = degreecount2()
    if (degreecount2() != degcount):
        # Degree counts are not period-2:
        return (-1, -1, -1)

    # Degree counts of each standard spaceship:
    hwssa = [1,4,6,2,0,0,0,0,0,0,0,0,4,4,6,1,2,1]
    mwssa = [2,2,5,2,0,0,0,0,0,0,0,0,4,4,4,1,2,0]
    lwssa = [1,2,4,2,0,0,0,0,0,0,0,0,4,4,2,2,0,0]
    hwssb = [0,0,0,4,4,6,1,2,1,1,4,6,2,0,0,0,0,0]
    mwssb = [0,0,0,4,4,4,1,2,0,2,2,5,2,0,0,0,0,0]
    lwssb = [0,0,0,4,4,2,2,0,0,1,2,4,2,0,0,0,0,0]

    # Calculate the number of standard spaceships in each phase:
    hacount = degcount[17]
    macount = degcount[16]//2 - hacount
    lacount = (degcount[15] - hacount - macount)//2
    hbcount = degcount[8]
    mbcount = degcount[7]//2 - hbcount
    lbcount = (degcount[6] - hbcount - mbcount)//2

    # Determine the expected degcount given the calculated quantities:
    pcounts = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    pcounts = list(map(lambda x, y: x + y, pcounts, [hacount*x for x in hwssa]))
    pcounts = list(map(lambda x, y: x + y, pcounts, [macount*x for x in mwssa]))
    pcounts = list(map(lambda x, y: x + y, pcounts, [lacount*x for x in lwssa]))
    pcounts = list(map(lambda x, y: x + y, pcounts, [hbcount*x for x in hwssb]))
    pcounts = list(map(lambda x, y: x + y, pcounts, [mbcount*x for x in mwssb]))
    pcounts = list(map(lambda x, y: x + y, pcounts, [lbcount*x for x in lwssb]))

    # Compare the observed and expected degcounts (to eliminate nonstandard spaceships):
    if (pcounts != degcount):
        # Expected and observed values do not match:
        return (-1, -1, -1)

    # Return the combined numbers of *WSSes:
    return(lacount + lbcount, macount + mbcount, hacount + hbcount)


# Generates the helper rules for apgsearch, given a base outer-totalistic rule.
class RuleGenerator:

    def __init__(self):

        # Unless otherwise specified, assume standard B3/S23 rule:
        self.bee = [False, False, False, True, False, False, False, False, False]
        self.ess = [False, False, True, True, False, False, False, False, False]
        self.alphanumeric = "B3S23"
        self.slashed = "B3/S23"

    # Save all helper rules:
    def saveAllRules(self):

        self.saveClassifyObjects()
        self.saveCoalesceObjects()
        self.saveExpungeObjects()
        self.saveExpungeGliders()
        self.saveIdentifyGliders()
        self.saveHandlePlumes()
        self.savePercolateInfection()
        self.saveEradicateInfection()
        self.saveContagiousLife()

    # Set outer-totalistic rule:
    def setrule(self, rulestring):

        mode = 0
        s = [False]*9
        b = [False]*9

        for c in rulestring:

            if ((c == 's') | (c == 'S')):
                mode = 0

            if ((c == 'b') | (c == 'B')):
                mode = 1

            if (c == '/'):
                mode = 1 - mode

            if ((ord(c) >= 48) & (ord(c) <= 56)):
                d = ord(c) - 48
                if (mode == 0):
                    s[d] = True
                else:
                    b[d] = True

        prefix = "B"
        suffix = "S"

        for i in range(9):
            if (b[i]):
                prefix += str(i)
            if (s[i]):
                suffix += str(i)

        self.alphanumeric = prefix + suffix
        self.slashed = prefix + "/" + suffix
        self.bee = b
        self.ess = s

    # Save a rule file:
    def saverule(self, name, comments, table, colours):

        ruledir = g.getdir("rules")
        filename = ruledir + name + ".rule"

        results = "@RULE " + name + "\n\n"
        results += "*** File autogenerated by saverule. ***\n\n"
        results += comments
        results += "\n\n@TABLE\n\n"
        results += table
        results += "\n\n@COLORS\n\n"
        results += colours

        # Only create a rule file if it doesn't already exist; this avoids
        # concurrency issues when booting an instance of apgsearch whilst
        # one is already running.
        if not os.path.exists(filename):
            try:
                f = open(filename, 'w')
                f.write(results)
                f.close()
            except:
                g.warn("Unable to create rule table:\n" + filename)

    # Defines a variable:
    def newvar(self, name, vallist):

        line = "var "+name+"={"
        for i in range(len(vallist)):
            if (i > 0):
                line += ','
            line += str(vallist[i])
        line += "}\n"

        return line

    # Defines a block of equivalent variables:
    def newvars(self, namelist, vallist):

        block = ""

        for name in namelist:
            block += self.newvar(name, vallist)

        block += "\n"

        return block

    def scoline(self, chara, charb, left, right, amount):

        line = str(left) + ","

        for i in range(8):
            if (i < amount):
                line += chara
            else:
                line += charb
            line += chr(97 + i)
            line += ","

        line += str(right) + "\n"

        return line

    def saveHandlePlumes(self):

        comments = """
This post-processes the output of ClassifyObjects to remove any
unwanted clustering of low-period objects appearing in puffer
exhaust.

state 0:  vacuum

state 7:  ON, still-life
state 8:  OFF, still-life

state 9:  ON, p2 oscillator
state 10: OFF, p2 oscillator

state 11: ON, higher-period object
state 12: OFF, higher-period object
"""
        table = """
n_states:17
neighborhood:Moore
symmetries:permute

var da={0,2,4,6,8,10,12,14,16}
var db={0,2,4,6,8,10,12,14,16}
var dc={0,2,4,6,8,10,12,14,16}
var dd={0,2,4,6,8,10,12,14,16}
var de={0,2,4,6,8,10,12,14,16}
var df={0,2,4,6,8,10,12,14,16}
var dg={0,2,4,6,8,10,12,14,16}
var dh={0,2,4,6,8,10,12,14,16}

var a={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var b={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var c={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var d={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var e={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var f={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var g={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var h={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}


8,da,db,dc,dd,de,df,dg,dh,0
10,da,db,dc,dd,de,df,dg,dh,0

9,a,b,c,d,e,f,g,h,1
10,a,b,c,d,e,f,g,h,2
"""
        colours = """
1  255  255  255
2  127  127  127
7    0    0  255
8    0    0  127
9  255    0    0
10 127    0    0
11   0  255    0
12   0  127    0
"""
        self.saverule("APG_HandlePlumesCorrected", comments, table, colours)

    def saveExpungeGliders(self):

        comments = """
This removes unwanted gliders.
It is mandatory that one first runs the rules CoalesceObjects,
IdentifyGliders and ClassifyObjects.

Run this for two generations, and observe the population
counts after 1 and 2 generations. This will give the
following data:

number of gliders = (p(1) - p(2))/5
"""
        table = """
n_states:17
neighborhood:Moore
symmetries:rotate4reflect

var a={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var b={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var c={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var d={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var e={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var f={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var g={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var h={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}

13,a,b,c,d,e,f,g,h,14
14,a,b,c,d,e,f,g,h,0
"""
        colours = """
0    0    0    0
1  255  255  255
2  127  127  127
7    0    0  255
8    0    0  127
9  255    0    0
10 127    0    0
11   0  255    0
12   0  127    0
13 255  255    0
14 127  127    0
"""
        self.saverule("APG_ExpungeGliders", comments, table, colours)

    def saveIdentifyGliders(self):

        comments = """
Run this after CoalesceObjects to find any gliders.

state 0:  vacuum
state 1:  ON
state 2:  OFF
"""
        table = """
n_states:17
neighborhood:Moore
symmetries:rotate4reflect

var a={0,2}
var b={0,2}
var c={0,2}
var d={0,2}
var e={0,2}
var f={0,2}
var g={0,2}
var h={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var i={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var j={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var k={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var l={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var m={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var n={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var o={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var p={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}
var q={3,4}
var r={9,10}
var s={11,12}

1,1,a,1,1,b,1,c,d,3
d,1,1,1,1,a,b,1,c,4

3,i,j,k,l,m,n,o,p,5
4,i,j,k,l,m,n,o,p,6

1,q,i,j,a,b,c,k,l,7
d,q,i,j,a,b,c,k,l,8
1,i,a,b,c,d,e,j,q,7
f,i,a,b,c,d,e,j,q,8

5,7,8,7,7,8,7,8,8,9
6,7,7,7,7,8,8,7,8,10
5,i,j,k,l,m,n,o,p,15
6,i,j,k,l,m,n,o,p,16
15,i,j,k,l,m,n,o,p,1
16,i,j,k,l,m,n,o,p,2

7,i,j,k,l,m,n,o,p,11
8,i,j,k,l,m,n,o,p,12

9,i,j,k,l,m,n,o,p,13
10,i,j,k,l,m,n,o,p,14
11,r,j,k,l,m,n,o,p,13
11,i,r,k,l,m,n,o,p,13
12,r,j,k,l,m,n,o,p,14
12,i,r,k,l,m,n,o,p,14

11,i,j,k,l,m,n,o,p,1
12,i,j,k,l,m,n,o,p,2
"""
        colours = """
0    0    0    0
1  255  255  255
2  127  127  127
7    0    0  255
8    0    0  127
9  255    0    0
10 127    0    0
11   0  255    0
12   0  127    0
13 255  255    0
14 127  127    0
"""
        self.saverule("APG_IdentifyGliders", comments, table, colours)

    def saveEradicateInfection(self):

        comments = """
To run after ContagiousLife to disinfect any cells in states 3 or 4.

state 0:  vacuum
state 1:  ON
state 2:  OFF
"""
        table = """
n_states:7
neighborhood:Moore
symmetries:permute

var a={0,1,2,3,4,5,6}
var b={0,1,2,3,4,5,6}
var c={0,1,2,3,4,5,6}
var d={0,1,2,3,4,5,6}
var e={0,1,2,3,4,5,6}
var f={0,1,2,3,4,5,6}
var g={0,1,2,3,4,5,6}
var h={0,1,2,3,4,5,6}
var i={0,1,2,3,4,5,6}

4,a,b,c,d,e,f,g,h,6
3,a,b,c,d,e,f,g,h,5
"""
        colours = """
0    0    0    0
1    0    0  255
2    0    0  127
3  255    0    0
4  127    0    0
5    0  255    0
6    0  127    0
"""
        self.saverule("APG_EradicateInfection", comments, table, colours)

    def savePercolateInfection(self):

        comments = """
Percolates any infection to all cells of that particular island.

state 0:  vacuum
state 1:  ON
state 2:  OFF
"""
        table = """
n_states:7
neighborhood:Moore
symmetries:permute

var a={0,1,2,3,4,5,6}
var b={0,1,2,3,4,5,6}
var c={0,1,2,3,4,5,6}
var d={0,1,2,3,4,5,6}
var e={0,1,2,3,4,5,6}
var f={0,1,2,3,4,5,6}
var g={0,1,2,3,4,5,6}
var h={0,1,2,3,4,5,6}
var i={0,1,2,3,4,5,6}

var q={3,4}
var da={2,4,6}
var la={1,3,5}

da,q,b,c,d,e,f,g,h,4
la,q,b,c,d,e,f,g,h,3
"""
        colours = """
0    0    0    0
1    0    0  255
2    0    0  127
3  255    0    0
4  127    0    0
5    0  255    0
6    0  127    0
"""
        self.saverule("APG_PercolateInfection", comments, table, colours)
        
    def saveExpungeObjects(self):

        comments = """
This removes unwanted monominos, blocks, blinkers and beehives.
It is mandatory that one first runs the rule ClassifyObjects.

Run this for four generations, and observe the population
counts after 0, 1, 2, 3 and 4 generations. This will give the
following data:

number of monominos = p(1) - p(0)
number of blocks = (p(2) - p(1))/4
number of blinkers = (p(3) - p(2))/5
number of beehives = (p(4) - p(3))/8
"""
        table = "n_states:17\n"
        table += "neighborhood:Moore\n"
        table += "symmetries:rotate4reflect\n\n"

        table += self.newvars(["a","b","c","d","e","f","g","h","i"], list(range(0, 17, 1)))

        table += """
# Monomino
7,0,0,0,0,0,0,0,0,0

# Death
6,a,b,c,d,e,f,g,h,0
a,6,b,c,d,e,f,g,h,0

# Block
7,7,7,7,0,0,0,0,0,1
1,1,1,1,0,0,0,0,0,0
1,a,b,c,d,e,f,g,h,7

# Blinker
10,0,0,0,9,9,9,0,0,2
9,9,10,0,0,0,0,0,10,3
2,a,b,c,d,e,f,g,h,10
3,a,b,c,d,e,f,g,h,9
9,2,0,3,0,2,0,3,0,6

# Beehive
7,0,7,8,7,0,0,0,0,1
7,0,0,7,8,8,7,0,0,1
8,7,7,8,7,7,0,7,0,4
4,1,1,4,1,1,0,1,0,5
4,a,b,c,d,e,f,g,h,8
5,5,b,c,d,e,f,g,h,6
5,a,b,c,d,e,f,g,h,15
15,a,b,c,d,e,f,g,h,8
"""

        colours = """
0    0    0    0
1  255  255  255
2  127  127  127
7    0    0  255
8    0    0  127
9  255    0    0
10 127    0    0
11   0  255    0
12   0  127    0
13 255  255    0
14 127  127    0
"""
        self.saverule("APG_ExpungeObjects", comments, table, colours)

    def saveCoalesceObjects(self):

        comments = """
A variant of HistoricalLife which separates a field of ash into
distinct objects.

state 0:  vacuum
state 1:  ON
state 2:  OFF
"""
        table = "n_states:3\n"
        table += "neighborhood:Moore\n"
        table += "symmetries:permute\n\n"

        table += self.newvars(["a","b","c","d","e","f","g","h","i"], [0, 1, 2])
        table += self.newvars(["da","db","dc","dd","de","df","dg","dh","di"], [0, 2])
        table += self.newvars(["la","lb","lc","ld","le","lf","lg","lh","li"], [1])

        minperc = 10

        for i in range(9):
            if (self.bee[i]):
                if (minperc == 10):
                    minperc = i
                table += self.scoline("l","d",0,1,i)
                table += self.scoline("l","d",2,1,i)
            if (self.ess[i]):
                table += self.scoline("l","d",1,1,i)

        table += "\n# Bridge inductors\n"

        for i in range(9):
            if (i >= minperc):
                table += self.scoline("l","d",0,2,i)

        table += self.scoline("","",1,2,0)

        colours = """
0    0    0    0
1  255  255  255
2  127  127  127
"""
        self.saverule("APG_CoalesceObjects_"+self.alphanumeric, comments, table, colours)

    def saveClassifyObjects(self):

        comments = """
This passively classifies objects as either still-lifes, p2 oscillators
or higher-period oscillators. It is mandatory that one first runs the
rule CoalesceObjects.

state 0:  vacuum
state 1:  input ON
state 2:  input OFF

state 3:  ON, will die
state 4:  OFF, will remain off
state 5:  ON, will survive
state 6:  OFF, will become alive

state 7:  ON, still-life
state 8:  OFF, still-life

state 9:  ON, p2 oscillator
state 10: OFF, p2 oscillator

state 11: ON, higher-period object
state 12: OFF, higher-period object
"""
        table = "n_states:17\n"
        table += "neighborhood:Moore\n"
        table += "symmetries:permute\n\n"

        table += self.newvars(["a","b","c","d","e","f","g","h","i"], list(range(0, 17, 1)))
        table += self.newvars(["la","lb","lc","ld","le","lf","lg","lh","li"], list(range(1, 17, 2)))
        table += self.newvars(["da","db","dc","dd","de","df","dg","dh","di"], list(range(0, 17, 2)))
        table += self.newvars(["pa","pb","pc","pd","pe","pf","pg","ph","pi"], [0, 3, 4])
        table += self.newvars(["qa","qb","qc","qd","qe","qf","qg","qh","qi"], [5, 6])

        for i in range(9):
            if (self.bee[i]):
                table += self.scoline("l","d",2,6,i)
                table += self.scoline("q","p",3,9,i)
                table += self.scoline("q","p",4,12,i)
            if (self.ess[i]):
                table += self.scoline("l","d",1,5,i)
                table += self.scoline("q","p",5,7,i)
                table += self.scoline("q","p",6,12,i)
        table += self.scoline("","",2,4,0)
        table += self.scoline("","",1,3,0)
        table += self.scoline("","",5,11,0)
        table += self.scoline("","",3,11,0)
        table += self.scoline("","",4,8,0)
        table += self.scoline("","",6,10,0)

        table += """
# Propagate interestingness
7,11,b,c,d,e,f,g,h,11
7,12,b,c,d,e,f,g,h,11
7,9,b,c,d,e,f,g,h,9
7,10,b,c,d,e,f,g,h,9
8,11,b,c,d,e,f,g,h,12
8,12,b,c,d,e,f,g,h,12
8,9,b,c,d,e,f,g,h,10
8,10,b,c,d,e,f,g,h,10

7,13,b,c,d,e,f,g,h,11
7,14,b,c,d,e,f,g,h,11
8,13,b,c,d,e,f,g,h,14
8,14,b,c,d,e,f,g,h,14
9,13,b,c,d,e,f,g,h,11
9,14,b,c,d,e,f,g,h,11
10,13,b,c,d,e,f,g,h,14
10,14,b,c,d,e,f,g,h,14

9,11,b,c,d,e,f,g,h,11
9,12,b,c,d,e,f,g,h,11
10,11,b,c,d,e,f,g,h,12
10,12,b,c,d,e,f,g,h,12

13,11,b,c,d,e,f,g,h,11
13,12,b,c,d,e,f,g,h,11
14,11,b,c,d,e,f,g,h,12
14,12,b,c,d,e,f,g,h,12
13,9,b,c,d,e,f,g,h,11
14,9,b,c,d,e,f,g,h,12
"""

        colours = """
0    0    0    0
1  255  255  255
2  127  127  127
7    0    0  255
8    0    0  127
9  255    0    0
10 127    0    0
11   0  255    0
12   0  127    0
13 255  255    0
14 127  127    0
"""
        self.saverule("APG_ClassifyObjects_"+self.alphanumeric, comments, table, colours)

    def saveContagiousLife(self):

        comments = """
A variant of HistoricalLife used for detecting dependencies between
islands.

state 0:  vacuum
state 1:  ON
state 2:  OFF
"""
        table = "n_states:7\n"
        table += "neighborhood:Moore\n"
        table += "symmetries:permute\n\n"

        table += self.newvars(["a","b","c","d","e","f","g","h","i"], list(range(0, 7, 1)))
        table += self.newvars(["la","lb","lc","ld","le","lf","lg","lh","li"], list(range(1, 7, 2)))
        table += self.newvars(["da","db","dc","dd","de","df","dg","dh","di"], list(range(0, 7, 2)))
        table += self.newvar("p",[3, 4])
        table += self.newvars(["ta","tb","tc","td","te","tf","tg","th","ti"], [3])
        table += self.newvars(["qa","qb","qc","qd","qe","qf","qg","qh","qi"], [0, 1, 2, 4, 5, 6])

        for i in range(9):
            if (self.bee[i]):
                table += self.scoline("l","d",4,3,i)
                table += self.scoline("l","d",2,1,i)
                table += self.scoline("l","d",0,1,i)
                table += self.scoline("l","d",6,5,i)
                table += self.scoline("t","q",0,4,i)
            if (self.ess[i]):
                table += self.scoline("l","d",3,3,i)
                table += self.scoline("l","d",5,5,i)
                table += self.scoline("l","d",1,1,i)

        table += "# Default behaviour (death):\n"
        table += self.scoline("","",1,2,0)
        table += self.scoline("","",5,6,0)
        table += self.scoline("","",3,4,0)

        colours = """
0    0    0    0
1    0    0  255
2    0    0  127
3  255    0    0
4  127    0    0
5    0  255    0
6    0  127    0
"""
        self.saverule("APG_ContagiousLife_"+self.alphanumeric, comments, table, colours)


class Soup:

    def __init__(self):

        # The rule generator:
        self.rg = RuleGenerator()

        # Should we skip error-correction:
        self.skipErrorCorrection = False

        # A dict mapping binary representations of small possibly-pseudo-objects
        # to their equivalent canonised representation.
        #
        # This is many-to-one, as (for example) all of these will map to
        # the same pseudo-object (namely the beacon on block):
        #
        # ..**.**  ..**.**  **.....                           **.....
        # ..**.**  ...*.**  **.....                           *......
        # **.....  *......  ..**...                           ...*.**
        # **.....  **.....  ..**... [...12 others omitted...] ..**.**
        # .......  .......  .......                           .......
        # .......  .......  ..**...                           .......
        # .......  .......  ..**...                           .......
        #
        # The first few soups are much slower to process, as objects are being
        # entered into the cache.
        self.cache = {}

        # A dict to store memoized decompositions of possibly-pseudo-objects
        # into constituent parts. This is initialised with the unique minimal
        # pseudo-still-life (two blocks on lock) that cannot be automatically
        # separated by the routine pseudo_bangbang(). Any larger objects are
        # ambiguous, such as this one:
        #
        #     *
        #    * * **
        #     ** **
        #
        #    * *** *
        #    ** * **
        #
        # Is it a (block on (lock on boat)) or ((block on lock) on boat)?
        # Ahh, the joys of non-associativity.
        #
        # See http://paradise.caltech.edu/~cook/Workshop/CAs/2DOutTot/Life/StillLife/StillLifeTheory.html
        self.decompositions = {"xs18_3pq3qp3": ["xs14_3123qp3", "xs4_33"]}

        # A dict of objects in the form {"identifier": ("common name", points)}
        #
        # As a rough heuristic, an object is worth 15 + log2(n) points if it
        # is n times rarer than the pentadecathlon.
        #
        # Still-lifes are limited to 10 points.
        # p2 oscillators are limited to 20 points.
        # p3 and p4 oscillators are limited to 30 points.
        self.commonnames = {"xp3_co9nas0san9oczgoldlo0oldlogz1047210127401": ("pulsar", 8),
                       "xp15_4r4z4r4": ("pentadecathlon", 15),
                       "xp2_2a54": ("clock", 16),
                       "xp2_31ago": ("bipole", 17),
                       "xp2_0g0k053z32": ("quadpole", 18),
                       "xp2_g8gid1e8z1226": ("great on-off", 19),
                       "xp2_rhewehr": ("spark coil", 19),
                       "xp8_gk2gb3z11": ("figure-8", 20),
                       "xp4_37bkic": ("mold", 21),
                       "xp2_31a08zy0123cko": ("quadpole on ship", 20),
                       "xp2_g0k053z11": ("tripole", 20),
                       "xp4_ssj3744zw3": ("mazing", 23),
                       "xp8_g3jgz1ut": ("blocker", 24),
                       "xp3_695qc8zx33": ("jam", 24),
                       "xp30_w33z8kqrqk8zzzw33": ("cis-queen-bee-shuttle", 24),
                       "xp30_w33z8kqrqk8zzzx33": ("trans-queen-bee-shuttle", 24),
                       "xp4_8eh5e0e5he8z178a707a871": ("cloverleaf", 25),
                       "xp5_idiidiz01w1": ("octagon II", 26),
                       "xp6_ccb7w66z066": ("unix", 26),
                       "xp14_j9d0d9j": ("tumbler", 27),
                       "xp3_025qzrq221": ("trans-tub-eater", 28),
                       "xp3_4hh186z07": ("caterer", 29),
                       "xp3_025qz32qq1": ("cis-tub-eater", 30),
                       "xp8_wgovnz234z33": ("Tim Coe's p8", 31),
                       "xp5_3pmwmp3zx11": ("fumarole", 33),
                       "xp46_330279cx1aad3y833zx4e93x855bc": ("cis-twin-bees-shuttle", 35),
                       "xp46_330279cx1aad3zx4e93x855bcy8cc": ("trans-twin-bees-shuttle", 35),
                       "yl144_1_16_afb5f3db909e60548f086e22ee3353ac": ("block-laying switch engine", 16),
                       "yl384_1_59_7aeb1999980c43b4945fb7fcdb023326": ("glider-producing switch engine", 17),
                       "xp10_9hr": ("[HighLife] p10", 6),
                       "xp7_13090c8": ("[HighLife] p7", 9),
                       "xq48_07z8ca7zy1e531": ("[HighLife] bomber", 9),
                       "xq4_153": ("glider", 0),
                       "xq4_6frc": ("lightweight spaceship", 7),
                       "xq4_27dee6": ("middleweight spaceship", 9),
                       "xq4_27deee6": ("heavyweight spaceship", 12),
                       "xq7_3nw17862z6952": ("loafer", 70),
                       "xp2_7": ("blinker", 0),
                       "xs4_33": ("block", 0),
                       "xs4_252": ("tub", 0),
                       "xs5_253": ("boat", 0),
                       "xs6_bd": ("snake", 0),
                       "xs6_356": ("ship", 0),
                       "xs6_696": ("beehive", 0),
                       "xs6_25a4": ("barge", 0),
                       "xs6_39c": ("carrier", 0),
                       "xp2_7e": ("toad", 0),
                       "xp2_318c": ("beacon", 0),
                       "xs7_3lo": ("long snake", 0),
                       "xs7_25ac": ("long boat", 0),
                       "xs7_178c": ("eater", 0),
                       "xs7_2596": ("loaf", 0),
                       "xs8_178k8": ("twit", 0),
                       "xs8_32qk": ("hook with tail", 0),
                       "xs8_69ic": ("mango", 0),
                       "xs8_6996": ("pond", 0),
                       "xs8_25ak8": ("long barge", 0),
                       "xs8_3pm": ("shillelagh", 0),
                       "xs8_312ko": ("canoe", 0),
                       "xs8_31248c": ("very long snake", 0),
                       "xs8_35ac": ("long ship", 0),
                       "xs12_g8o653z11": ("ship-tie", 0),
                       "xs14_g88m952z121": ("half-bakery", 0),
                       "xs14_69bqic": ("paperclip", 0),
                       "xs9_31ego": ("integral sign", 0),
                       "xs10_g8o652z01": ("boat-tie", 0),
                       "xs14_g88b96z123": ("big ess", 0),
                       "xs16_g88m996z1221": ("bipond", 0),
                       "xs12_raar": ("table on table", 0),
                       "xs9_4aar": ("hat", 0),
                       "xs10_35ako": ("very long ship", 0),
                       "xs9_178ko": ("trans boat with tail", 0),
                       "xs15_354cgc453": ("moose antlers", 0),
                       "xs14_6970796": ("cis-mirrored r-bee", 0),
                       "xs10_32qr": ("block on table", 0),
                       "xs16_j1u0696z11": ("beehive on dock", 0),
                       "xs14_j1u066z11": ("block on dock", 0),
                       "xs11_g8o652z11": ("boat tie ship", 0),
                       "xs9_25ako": ("very long boat", 0),
                       "xs16_69egmiczx1": ("scorpion", 0),
                       "xs18_rhe0ehr": ("dead spark coil", 0),
                       "xs17_2ege1ege2": ("twinhat", 0),
                       "xs10_178kk8": ("beehive with tail", 0),
                       "xs10_69ar": ("loop", 0),
                       "xs14_69bo8a6": ("fourteener", 0),
                       "xs14_39e0e93": ("bookends", 0),
                       "xs9_178kc": ("cis boat with tail", 0),
                       "xs12_330f96": ("block and cap", 0),
                       "xs10_358gkc": ("10.003",0),
                       "xs12_330fho": ("trans block and longhook", 0),
                       "xs10_g0s252z11": ("prodigal sign", 0),
                       "xs11_g0s453z11": ("elevener", 0),
                       "xs14_6is079c": ("cis-rotated hook", 0),
                       "xs14_69e0eic": ("trans-mirrored R-bee", 0),
                       "xs11_ggm952z1": ("trans loaf with tail", 0),
                       "xs15_j1u06a4z11": ("cis boat and dock", 0),
                       "xs20_3lkkl3z32w23": ("mirrored dock", 0),
                       "xs12_178br": ("12.003",0),
                       "xs12_3hu066": ("cis block and longhook", 0),
                       "xs12_178c453": ("eater with nine", 0),
                       "xs10_0drz32": ("broken snake", 0),
                       "xs9_312453": ("long shillelagh", 0),
                       "xs10_3215ac": ("boat with long tail", 0),
                       "xs14_39e0e96": ("cis-hook and R-bee", 0),
                       "xs13_g88m96z121": ("beehive at loaf", 0),
                       "xs14_39e0eic": ("trans hook and R-bee", 0),
                       "xs10_3542ac": ("S-ten", 0),
                       "xs15_259e0eic": ("trans R-bee and R-loaf", 0),
                       "xs11_178jd": ("11-loop", 0),
                       "xs9_25a84c": ("tub with long tail", 0),
                       "xs15_3lkm96z01": ("bee-hat", 0),
                       "xs14_g8o0e96z121": ("cis-rotated R-bee", 0),
                       "xs13_69e0mq": ("R-bee and snake", 0),
                       "xs11_69lic": ("11.003", 0),
                       "xs12_6960ui": ("beehive and table", 0),
                       "xs16_259e0e952": ("cis-mirrored R-loaf", 0),
                       "xs10_1784ko": ("8-snake-eater", 0),
                       "xs13_4a960ui": ("ortho loaf and table", 0),
                       "xs9_g0g853z11": ("long canoe", 0),
                       "xs18_69is0si96": ("[cis-mirrored R-mango]", 0),
                       "xs11_178kic": ("cis loaf with tail", 0),
                       "xs16_69bob96": ("symmetric scorpion", 0),
                       "xs13_0g8o653z121": ("longboat on ship", 0),
                       "xs12_o4q552z01": ("beehive at beehive", 0),
                       "xs10_ggka52z1": ("trans barge with tail", 0),
                       "xs12_256o8a6": ("eater on boat", 0),
                       "xs14_6960uic": ("beehive with cap", 0),
                       "xs12_2egm93": ("snorkel loop", 0),
                       "xs12_2egm96": ("beehive bend tail", 0),
                       "xs11_g0s253z11": ("trans boat with nine", 0),
                       "xs15_3lk453z121": ("trans boat and dock", 0),
                       "xs19_69icw8ozxdd11": ("[mango with block on dock]", 0),
                       "xs13_2530f96": ("[cis boat and cap]", 0),
                       "xs11_2530f9": ("cis boat and table", 0),
                       "xs14_4a9m88gzx121": ("[bi-loaf2]", 0),
                       "xs11_ggka53z1": ("trans longboat with tail", 0),
                       "xs18_2egm9a4zx346": ("[loaf eater tail]", 0),
                       "xs15_4a9raic": ("[15-bent-paperclip]", 0),
                       "xs11_3586246": ("[11-snake]",0),
                       "xs11_178b52": ("[11-boat wrap tail]", 0),
                       "xs14_08u1e8z321": ("[hat join hook]", 0),
                       "xs14_g4s079cz11": ("[cis-mirrored offset hooks]", 0),
                       "xs13_31egma4": ("[13-boat wrap eater]", 0),
                       "xs14_69960ui": ("pond and table", 0),
                       "xs13_255q8a6": ("[eater tie beehive]", 0),
                       "xs15_09v0ccz321": ("[hook join table and block]",0)}

        # First soup to contain a particular object:
        self.alloccur = {}

        # A tally of objects that have occurred during this run of apgsearch:
        self.objectcounts = {}

        # Any soups with positive scores, and the number of points.
        self.soupscores = {}

        # Temporary list of unidentified objects:
        self.unids = []

        # Things like glider guns and large oscillators belong here:
        self.superunids = []
        self.gridsize = 0
        self.resets = 0

        # For profiling purposes:
        self.qlifetime = 0.0
        self.ruletime = 0.0
        self.gridtime = 0.0

    # Increment object count by given value:
    def incobject(self, obj, incval):
        if (incval > 0):
            if obj in self.objectcounts:
                self.objectcounts[obj] = self.objectcounts[obj] + incval
            else:
                self.objectcounts[obj] = incval

    # Increment soup score by given value:
    def awardpoints(self, soupid, incval):
        if (incval > 0):
            if soupid in self.soupscores:
                self.soupscores[soupid] = self.soupscores[soupid] + incval
            else:
                self.soupscores[soupid] = incval

    # Increment soup score by appropriate value:
    def awardpoints2(self, soupid, obj):

        # Record the occurrence of this object:
        if (obj in self.alloccur):
            if (len(self.alloccur[obj]) < 10):
                if (soupid not in self.alloccur[obj]):
                    self.alloccur[obj] += [soupid]
        else:
            self.alloccur[obj] = [soupid]
        
        if obj in self.commonnames:
            self.awardpoints(soupid, self.commonnames[obj][1])
        elif (obj[0] == 'x'):
            prefix = obj.split('_')[0]
            prenum = int(prefix[2:])
            if (obj[1] == 's'):
                self.awardpoints(soupid, min(prenum, 20)) # for still-lifes, award one point per constituent cell (max 20)
            elif (obj[1] == 'p'):
                if (prenum == 2):
                    self.awardpoints(soupid, 20) # p2 oscillators are limited to 20 points
                elif ((prenum == 3) | (prenum == 4)):
                    self.awardpoints(soupid, 30) # p3 and p4 oscillators are limited to 30 points
                else:
                    self.awardpoints(soupid, 40)
            else:
                self.awardpoints(soupid, 50)
        else:
            self.awardpoints(soupid, 60)

    # Assuming the pattern has stabilised, perform a census:
    def census(self, stepsize):

        g.setrule("APG_CoalesceObjects_" + self.rg.alphanumeric)
        g.setbase(2)
        g.setstep(stepsize)
        g.step()

        # apgsearch theoretically supports up to 2^14 rules, whereas the Guy
        # glider is only stable in 2^8 rules. Ensure that this is one of these
        # rules by doing some basic Boolean arithmetic.
        #
        # This should be parsed as `gliders exist', not `glider sexist':
        glidersexist = self.rg.ess[2] & self.rg.ess[3] & (not self.rg.ess[1]) & (not self.rg.ess[4])
        glidersexist = glidersexist & (not (self.rg.bee[4] | self.rg.bee[5]))

        if (glidersexist):
            g.setrule("APG_IdentifyGliders")
            g.setbase(2)
            g.setstep(2)
            g.step()

        g.setrule("APG_ClassifyObjects_" + self.rg.alphanumeric)
        g.setbase(2)
        g.setstep(max(8, stepsize))
        g.step()

        # Only do this if we have an infinite-growth pattern:
        if (stepsize > 8):
            g.setrule("APG_HandlePlumesCorrected")
            g.setbase(2)
            g.setstep(1)
            g.step()
            g.setrule("APG_ClassifyObjects_" + self.rg.alphanumeric)
            g.setstep(stepsize)
            g.step()

        # Remove any gliders:
        if (glidersexist):
            g.setrule("APG_ExpungeGliders")
            g.run(1)
            pop5 = int(g.getpop())
            g.run(1)
            pop6 = int(g.getpop())
            self.incobject("xq4_153", (pop5 - pop6)//5)

        # Remove any blocks, blinkers and beehives:
        g.setrule("APG_ExpungeObjects")
        pop0 = int(g.getpop())
        g.run(1)
        pop1 = int(g.getpop())
        g.run(1)
        pop2 = int(g.getpop())
        g.run(1)
        pop3 = int(g.getpop())
        g.run(1)
        pop4 = int(g.getpop())

        # Blocks, blinkers and beehives removed by ExpungeObjects:
        self.incobject("xs1_1", (pop0-pop1))
        self.incobject("xs4_33", (pop1-pop2)//4)
        self.incobject("xp2_7", (pop2-pop3)//5)
        self.incobject("xs6_696", (pop3-pop4)//8)

    # Removes an object incident with (ix, iy) and returns the cell list:
    def grabobj(self, ix, iy):

        allcells = [ix, iy, g.getcell(ix, iy)]
        g.setcell(ix, iy, 0)
        livecells = []
        deadcells = []

        marker = 0
        ll = 3

        while (marker < ll):
            x = allcells[marker]
            y = allcells[marker+1]
            z = allcells[marker+2]
            marker += 3

            if ((z % 2) == 1):
                livecells.append(x)
                livecells.append(y)
            else:
                deadcells.append(x)
                deadcells.append(y)

            for nx in range(x - 1, x + 2):
                for ny in range(y - 1, y + 2):

                    nz = g.getcell(nx, ny)
                    if (nz > 0):
                        allcells.append(nx)
                        allcells.append(ny)
                        allcells.append(nz)
                        g.setcell(nx, ny, 0)
                        ll += 3

        return livecells

    # Command to Grab, Remove and IDentify an OBJect:
    def gridobj(self, ix, iy, gsize, gspacing, pos):

        allcells = [ix, iy, g.getcell(ix, iy)]
        g.setcell(ix, iy, 0)
        livecells = []
        deadcells = []

        # This tacitly assumes the object is smaller than 1000-by-1000.
        # But this is okay, since it is only used by the routing logic.
        dleft = ix + 1000
        dright = ix - 1000
        dtop = iy + 1000
        dbottom = iy - 1000

        lleft = ix + 1000
        lright = ix - 1000
        ltop = iy + 1000
        lbottom = iy - 1000

        lpop = 0
        dpop = 0

        marker = 0
        ll = 3

        while (marker < ll):
            x = allcells[marker]
            y = allcells[marker+1]
            z = allcells[marker+2]
            marker += 3

            if ((z % 2) == 1):
                livecells.append(x)
                livecells.append(y)
                lleft = min(lleft, x)
                lright = max(lright, x)
                ltop = min(ltop, y)
                lbottom = max(lbottom, y)
                lpop += 1
            else:
                deadcells.append(x)
                deadcells.append(y)
                dleft = min(dleft, x)
                dright = max(dright, x)
                dtop = min(dtop, y)
                dbottom = max(dbottom, y)
                dpop += 1

            for nx in range(x - 1, x + 2):
                for ny in range(y - 1, y + 2):

                    nz = g.getcell(nx, ny)
                    if (nz > 0):
                        allcells.append(nx)
                        allcells.append(ny)
                        allcells.append(nz)
                        g.setcell(nx, ny, 0)
                        ll += 3

        lwidth = max(0, 1 + lright - lleft)
        lheight = max(0, 1 + lbottom - ltop)
        dwidth = max(0, 1 + dright - dleft)
        dheight = max(0, 1 + dbottom - dtop)

        llength = max(lwidth, lheight)
        lbreadth = min(lwidth, lheight)
        dlength = max(dwidth, dheight)
        dbreadth = min(dwidth, dheight)

        self.gridsize = max(self.gridsize, llength)

        objid = "unidentified"
        bitstring = 0

        if (lpop == 0):
            objid = "nothing"
        else:
            if ((lwidth <= 7) & (lheight <= 7)):
                for i in range(0, lpop*2, 2):
                    bitstring += (1 << ((livecells[i] - lleft) + 7*(livecells[i + 1] - ltop)))

                if bitstring in self.cache:
                    objid = self.cache[bitstring]

        if (objid == "unidentified"):
            # This has passed through the routing logic without being identified,
            # so save it in a temporary list for later identification:
            self.unids.append(bitstring)
            self.unids.append(livecells)
            self.unids.append(lleft)
            self.unids.append(ltop)
        elif (objid != "nothing"):
            # The object is non-empty, so add it to the census:
            ux = int(0.5 + float(lleft)/float(gspacing))
            uy = int(0.5 + float(ltop)/float(gspacing))
            soupid = ux + (uy * gsize) + pos

            # Check whether the cached object is in the set of decompositions
            # (this is usually the case, unless for example it is a high-period
            # albeit small spaceship):
            if objid in self.decompositions:            
                for comp in self.decompositions[objid]:
                    self.incobject(comp, 1)
                    self.awardpoints2(soupid, comp)
            else:
                self.incobject(objid, 1)
                self.awardpoints2(soupid, objid)


    # Tests for population periodicity:
    def naivestab(self, period, security, length):

        depth = 0
        prevpop = 0
        for i in range(length):
            g.run(period)
            currpop = int(g.getpop())
            if (currpop == prevpop):
                depth += 1
            else:
                depth = 0
            prevpop = currpop
            if (depth == security):
                # Population is periodic.
                return True

        return False

    # This should catch most short-lived soups with few gliders produced:
    def naivestab2(self, period, length):

        for i in range(length):
            r = g.getrect()
            if (len(r) == 0):
                return True
            pop0 = int(g.getpop())
            g.run(period)
            hash1 = g.hash(r)
            pop1 = int(g.getpop())
            g.run(period)
            hash2 = g.hash(r)
            pop2 = int(g.getpop())

            if ((hash1 == hash2) & (pop0 == pop1) & (pop1 == pop2)):

                if (g.getrect() == r):
                    return True
                
                g.run((2*int(max(r[2], r[3])/period)+1)*period)
                hash3 = g.hash(r)
                pop3 = int(g.getpop())
                if ((hash2 == hash3) & (pop2 == pop3)):
                    return True

        return False
            
    # Runs a pattern until stabilisation with a 99.99996% success rate.
    # False positives are handled by a later error-correction stage.
    def stabilise3(self):

        # Phase I of stabilisation detection, designed to weed out patterns
        # that stabilise into a cluster of low-period oscillators within
        # about 6000 generations.

        if (self.naivestab2(12, 10)):
            return 4;

        if (self.naivestab(12, 30, 200)):
            return 4;

        if (self.naivestab(30, 30, 200)):
            return 5;

        # Phase II of stabilisation detection, which is much more rigorous
        # and based on oscar.py.

        # Should be sufficient:
        prect = [-2000, -2000, 4000, 4000]

        # initialize lists
        hashlist = []        # for pattern hash values
        genlist = []         # corresponding generation counts

        for j in range(4000):

            g.run(30)

            h = g.hash(prect)

            # determine where to insert h into hashlist
            pos = 0
            listlen = len(hashlist)
            while pos < listlen:
                if h > hashlist[pos]:
                    pos += 1
                elif h < hashlist[pos]:
                    # shorten lists and append info below
                    del hashlist[pos : listlen]
                    del genlist[pos : listlen]
                    break
                else:
                    period = (int(g.getgen()) - genlist[pos])

                    prevpop = g.getpop()

                    for i in range(20):
                        g.run(period)
                        currpop = g.getpop()
                        if (currpop != prevpop):
                            period = max(period, 4000)
                            break
                        prevpop = currpop
                        
                    return max(1 + int(math.log(period, 2)),3)

            hashlist.insert(pos, h)
            genlist.insert(pos, int(g.getgen()))

        g.setalgo("HashLife")
        g.setrule(self.rg.slashed)
        g.setbase(2)
        g.setstep(16)
        g.step()
        stepsize = 12
        g.setalgo("QuickLife")
        g.setrule(self.rg.slashed)

        return 12

    # Differs from oscar.py in that it detects absolute cycles, not eventual cycles.
    def bijoscar(self, maxsteps):

        initpop = int(g.getpop())
        initrect = g.getrect()
        if (len(initrect) == 0):
            return 0
        inithash = g.hash(initrect)

        for i in range(maxsteps):

            g.run(1)

            if (int(g.getpop()) == initpop):

                prect = g.getrect()
                phash = g.hash(prect)

                if (phash == inithash):

                    period = i + 1

                    if (prect == initrect):
                        return period
                    else:
                        return -period
        return -1

    # For a non-moving unidentified object, we check the dictionary of
    # memoized decompositions of possibly-pseudo-objects. If the object is
    # not already in the dictionary, it will be memoized.
    #
    # Low-period spaceships are also separated by this routine, although
    # this is less important now that there is a more bespoke prodecure
    # to handle disjoint unions of standard spaceships.
    #
    # @param moving  a bool which specifies whether the object is moving
    def enter_unid(self, unidname, soupid, moving):

        if not(unidname in self.decompositions):

            # Separate into pure components:
            if (moving):
                g.setrule("APG_CoalesceObjects_" + self.rg.alphanumeric)
                g.setbase(2)
                g.setstep(3)
                g.step()
            else:
                pseudo_bangbang(self.rg.alphanumeric)

            listoflists = [] # which incidentally don't contain themselves.

            # Someone who plays the celllo:
            celllist = g.join(g.getcells(g.getrect()), [0])

            for i in range(0, len(celllist)-1, 3):
                if (g.getcell(celllist[i], celllist[i+1]) != 0):
                    livecells = self.grabobj(celllist[i], celllist[i+1])
                    if (len(livecells) > 0):
                        listoflists.append(livecells)

            listofobjs = []

            for livecells in listoflists:

                g.new("Subcomponent")
                g.setalgo("QuickLife")
                g.setrule(self.rg.slashed)
                g.putcells(livecells)
                period = self.bijoscar(1000)
                canonised = canonise(abs(period))
                if (period < 0):
                    listofobjs.append("xq"+str(0-period)+"_"+canonised)
                elif (period == 1):
                    listofobjs.append("xs"+str(len(livecells)//2)+"_"+canonised)
                else:
                    listofobjs.append("xp"+str(period)+"_"+canonised)

            self.decompositions[unidname] = listofobjs

        # Actually add to the census:
        for comp in self.decompositions[unidname]:
            self.incobject(comp, 1)
            self.awardpoints2(soupid, comp)

    # This function has lots of arguments (hence the name):
    #
    # @param gsize     the square-root of the number of soups per page
    # @param gspacing  the minimum distance between centres of soups
    # @param ashes     a list of cell lists
    # @param stepsize  binary logarithm of amount of time to coalesce objects
    # @param intergen  binary logarithm of amount of time to run HashLife
    # @param pos       the index of the first soup on the page
    def teenager(self, gsize, gspacing, ashes, stepsize, intergen, pos):

        # For error-correction:
        if (intergen > 0):
            g.setalgo("HashLife")
            g.setrule(self.rg.slashed)

        # If this gets incremented, we panic and perform error-correction:
        pathological = 0

        # Draw the soups:
        for i in range(gsize * gsize):

            x = int(i % gsize)
            y = int(i // gsize)

            g.putcells(ashes[3*i], gspacing * x, gspacing * y)

        # Because why not?
        g.fit()
        g.update()

        # For error-correction:
        if (intergen > 0):
            g.setbase(2)
            g.setstep(intergen)
            g.step()

        # Apply rules to coalesce objects and expunge annoyances such as
        # blocks, blinkers, beehives and gliders:
        start_time = time.process_time()
        self.census(stepsize)
        end_time = time.process_time()
        self.ruletime += (end_time - start_time)

        # Now begin identifying objects:
        start_time = time.process_time()
        celllist = g.join(g.getcells(g.getrect()), [0])

        if (len(celllist) > 2):
            for i in range(0, len(celllist)-1, 3):
                if (g.getcell(celllist[i], celllist[i+1]) != 0):
                    self.gridobj(celllist[i], celllist[i+1], gsize, gspacing, pos)

        # If we have leftover unidentified objects, attempt to canonise them:
        while (len(self.unids) > 0):
            ux = int(0.5 + float(self.unids[-2])/float(gspacing))
            uy = int(0.5 + float(self.unids[-1])/float(gspacing))
            soupid = ux + (uy * gsize) + pos
            unidname = self.process_unid()
            if (unidname == "PATHOLOGICAL"):
                pathological += 1
            if (unidname != "nothing"):

                if ((unidname[0] == 'U') & (unidname[1] == 'S') & (unidname[2] == 'S')):
                    
                    # Union of standard spaceships:
                    countlist = unidname.split('_')
                    
                    self.incobject("xq4_6frc", int(countlist[1]))
                    for i in range(int(countlist[1])):
                        self.awardpoints2(soupid, "xq4_6frc")

                    self.incobject("xq4_27dee6", int(countlist[2]))
                    for i in range(int(countlist[2])):
                        self.awardpoints2(soupid, "xq4_27dee6")
                        
                    self.incobject("xq4_27deee6", int(countlist[3]))
                    for i in range(int(countlist[3])):
                        self.awardpoints2(soupid, "xq4_27deee6")
                        
                elif ((unidname[0] == 'x') & ((unidname[1] == 's') | (unidname[1] == 'p'))):
                    self.enter_unid(unidname, soupid, False)
                else:
                    if ((unidname[0] == 'x') & (unidname[1] == 'q') & (unidname[3] == '_')):
                        # Separates low-period (<= 9) non-standard spaceships in medium proximity:
                        self.enter_unid(unidname, soupid, True)
                    else:
                        self.incobject(unidname, 1)
                        self.awardpoints2(soupid, unidname)

        end_time = time.process_time()
        self.gridtime += (end_time - start_time)

        return pathological

    def stabilise_soups_parallel(self, root, pos, gsize, sym):

        souplist = [[sym, root + str(pos + i)] for i in range(gsize * gsize)]

        return self.stabilise_soups_parallel_orig(gsize, souplist, pos)

    def stabilise_soups_parallel_list(self, gsize, stringlist, pos):

        souplist = [s.split('/') for s in stringlist]

        return self.stabilise_soups_parallel_orig(gsize, souplist, pos)

    # This basically orchestrates everything:
    def stabilise_soups_parallel_orig(self, gsize, souplist, pos):

        ashes = []
        stepsize = 3

        g.new("Random soups")
        g.setalgo("QuickLife")
        g.setrule(self.rg.slashed)

        gspacing = 0

        # Generate and run the soups until stabilisation:
        for i in range(gsize * gsize):

            if (i < len(souplist)):

                sym = souplist[i][0]
                prehash = souplist[i][1]

                # Generate the soup from the SHA-256 of the concatenation of the
                # seed with the index:
                g.putcells(hashsoup(prehash, sym), 0, 0)

            # Run the soup until stabilisation:
            start_time = time.process_time()
            stepsize = max(stepsize, self.stabilise3())
            end_time = time.process_time()
            self.qlifetime += (end_time - start_time)

            # Ironically, the spelling of this variable is incurrrect:
            currrect = g.getrect()
            ashes.append(g.getcells(currrect))

            if (len(currrect) == 4):
                ashes.append(currrect[0])
                ashes.append(currrect[1])
                # Choose the grid spacing based on the size of the ash:
                gspacing = max(gspacing, 2*currrect[2])
                gspacing = max(gspacing, 2*currrect[3])
                g.select(currrect)
                g.clear(0)
            else:
                ashes.append(0)
                ashes.append(0)
            g.select([])

        # Account for any extra enlargement caused by running CoalesceObjects:
        gspacing += 2 ** (stepsize + 1) + 1000

        start_time = time.process_time()

        # Remember the dictionary, just in case we have a pathological object:
        prevdict = self.objectcounts.copy()
        prevscores = self.soupscores.copy()
        prevunids = self.superunids[:]

        # Process the soups:
        returncode = self.teenager(gsize, gspacing, ashes, stepsize, 0, pos)

        end_time = time.process_time()

        # Calculate the mean delay incurred (excluding qlifetime or error-correction):
        meandelay = (end_time - start_time) / (gsize * gsize)

        if (returncode > 0):
            if (self.skipErrorCorrection == False):
                # Arrrggghhhh, there's a pathological object! Usually this means
                # that naive stabilisation detection returned a false positive.
                self.resets += 1
                
                # Reset the object counts:
                self.objectcounts = prevdict
                self.soupscores = prevscores
                self.superunids = prevunids

                # 2^18 generations should suffice. This takes about 30 seconds in
                # HashLife, but error-correction only occurs very infrequently, so
                # this has a negligible impact on mean performance:
                gspacing += 2 ** 19
                stepsize = max(stepsize, 12)
                
                # Clear the universe:
                g.new("Error-correcting phase")
                self.teenager(gsize, gspacing, ashes, stepsize, 18, pos)

        # Erase any ashes. Not least because England usually loses...
        ashes = []

        # Return the mean delay so that we can use machine-learning to
        # find the optimal value of sqrtspp:
        return meandelay

    def reset(self):

        self.objectcounts = {}
        self.soupscores = {}
        self.alloccur = {}
        self.superunids = []
        self.unids = []

    # Pop the last unidentified object from the stack, and attempt to
    # ascertain its period and classify it.
    def process_unid(self):

        g.new("Unidentified object")
        g.setalgo("QuickLife")
        g.setrule(self.rg.slashed)
        y = self.unids.pop()
        x = self.unids.pop()
        livecells = self.unids.pop()
        bitstring = self.unids.pop()
        g.putcells(livecells, -x, -y, 1, 0, 0, 1, "or")
        period = self.bijoscar(1000)
        
        if (period == -1):
            # Infinite growth pattern, probably. Most infinite-growth
            # patterns are linear-growth (such as puffers, wickstretchers,
            # guns etc.) so we analyse to see whether we have a linear-
            # growth pattern:
            descriptor = linearlyse(1500)
            if (descriptor[0] == "y"):
                return descriptor

            # Similarly check for irregular power-law growth. This will
            # catch replicators, for instance. Spend around 375 000
            # generations; this seems like a reasonable amount of time.
            descriptor = powerlyse(8, 1500)
            if (descriptor[0] == "z"):
                return descriptor

            # It may be an unstabilised ember that slipped through the net,
            # but this will be handled by error-correction (unless it
            # persists another 2^18 gens, which is so unbelievably improbable
            # that you are more likely to be picked up by a passing ship in
            # the vacuum of space).
            self.superunids.append(livecells)
            self.superunids.append(x)
            self.superunids.append(y)
            
            return "PATHOLOGICAL"
        elif (period == 0):
            return "nothing"
        else:
            if (period == -4):

                triple = countxwsses()

                if (triple != (-1, -1, -1)):

                    # Union of Standard Spaceships:
                    return ("USS_" + str(triple[0]) + "_" + str(triple[1]) + "_" + str(triple[2]))

            
            canonised = canonise(abs(period))

            if (canonised == "#"):

                # Okay, we know that it's an oscillator or spaceship with
                # a non-astronomical period. But it's too large to canonise
                # in any of its phases (i.e. transcends a 40-by-40 box).
                self.superunids.append(livecells)
                self.superunids.append(x)
                self.superunids.append(y)
                
                # Append a suffix according to whether it is a still-life,
                # oscillator or moving object:
                if (period == 1):
                    descriptor = ("ov_s"+str(len(livecells)//2))
                elif (period > 0):
                    descriptor = ("ov_p"+str(period))
                else:
                    descriptor = ("ov_q"+str(0-period))

                return descriptor
            
            else:

                # Prepend a prefix according to whether it is a still-life,
                # oscillator or moving object:
                if (period == 1):
                    descriptor = ("xs"+str(len(livecells)//2)+"_"+canonised)
                elif (period > 0):
                    descriptor = ("xp"+str(period)+"_"+canonised)
                else:
                    descriptor = ("xq"+str(0-period)+"_"+canonised)

                if (bitstring > 0):
                    self.cache[bitstring] = descriptor

                return descriptor

    # This doesn't really do much, since unids should be empty and
    # actual pathological/oversized objects will rarely arise naturally.
    def display_unids(self):

        g.new("Unidentified objects")
        g.setalgo("QuickLife")
        g.setrule(self.rg.slashed)

        rowlength = 1 + int(math.sqrt(len(self.superunids)/3))

        for i in range(len(self.superunids)//3):

            xpos = i % rowlength
            ypos = int(i // rowlength)

            g.putcells(self.superunids[3*i], xpos * (self.gridsize + 8) - self.superunids[3*i + 1], ypos * (self.gridsize + 8) - self.superunids[3*i + 2], 1, 0, 0, 1, "or")

        g.fit()
        g.update()

    def compactify_scores(self):

        # Number of soups to record:
        highscores = 100
        ilist = sorted(iter(self.soupscores.items()), key=operator.itemgetter(1), reverse=True)

        # Empty the high score table:
        self.soupscores = {}
        
        for soupnum, score in ilist[:highscores]:
            self.soupscores[soupnum] = score

    # Saves a machine-readable textual file containing the census:
    def save_progress(self, numsoups, root, symmetry='C1', save_file=True, payosha256_key=None):

        g.show("Saving progress...")

        # Count the total number of objects:
        totobjs = 0
        censustable = "@CENSUS TABLE\n"
        tlist = sorted(iter(self.objectcounts.items()), key=operator.itemgetter(1), reverse=True)
        for objname, count in tlist:
            totobjs += count
            censustable += objname + " " + str(count) + "\n"

        g.show("Writing header information...")

        # The MD5 hash of the root string:
        md5root = hashlib.md5(root.encode('utf8')).hexdigest()

        # Header information:
        results = "@VERSION v1.1-4PGS34RCH\n"
        results += "@MD5 "+md5root+"\n"
        results += "@ROOT "+root+"\n"
        results += "@RULE "+self.rg.alphanumeric+"\n"
        results += "@SYMMETRY "+symmetry+"\n"
        results += "@NUM_SOUPS "+str(numsoups)+"\n"
        results += "@NUM_OBJECTS "+str(totobjs)+"\n"

        results += "\n"

        # Census table:
        results += censustable

        g.show("Compactifying score table...")

        results += "\n"

        # Number of soups to record:
        highscores = 100

        results += "@TOP "+str(highscores)+"\n"

        ilist = sorted(iter(self.soupscores.items()), key=operator.itemgetter(1), reverse=True)

        # Empty the high score table:
        self.soupscores = {}
        
        for soupnum, score in ilist[:highscores]:
            self.soupscores[soupnum] = score
            results += str(soupnum) + " " + str(score) + "\n"

        g.show("Saving soupids for rare objects...")

        results += "\n@SAMPLE_SOUPIDS\n"
        for objname, count in tlist:
            # blinkers and gliders have no alloccur[] entry for some reason,
            # so the line below avoids errors in B3/S23, maybe other rules too?
            if objname in self.alloccur:
                results += objname
                for soup in self.alloccur[objname]:
                    results += " " + str(soup)
                results += "\n"

        g.show("Writing progress file...")

        dirname = g.getdir("data")
        separator = dirname[-1]
        progresspath = dirname + "apgsearch" + separator + "progress" + separator
        if not os.path.exists(progresspath):
            os.makedirs(progresspath)

        filename = progresspath + "search_" + md5root + ".txt"
        
        try:
            f = open(filename, 'w')
            f.write(results)
            f.close()
        except:
            g.warn("Unable to create progress file:\n" + filename)

        if payosha256_key is not None:
            if (len(payosha256_key) > 0):
                return catagolue_results(results, payosha256_key, "post_apgsearch_haul")

    # Save soup RLE:
    def save_soup(self, root, soupnum, symmetry):

        # Soup pattern will be stored in a temporary directory:
        souphash = hashlib.sha256((root + str(soupnum)).encode('utf8'))
        rlepath = souphash.hexdigest()
        rlepath = g.getdir("temp") + rlepath + ".rle"
        
        results = "<a href=\"open:" + rlepath + "\">"
        results += str(soupnum)
        results += "</a>"

        # Try to write soup patterns to file "rlepath":
        try:
            g.store(hashsoup(root + str(soupnum), symmetry), rlepath)
        except:
            g.warn("Unable to create soup pattern:\n" + rlepath)

        return results
        
    # Display results in Help window:
    def display_census(self, numsoups, root, symmetry):

        dirname = g.getdir("data")
        separator = dirname[-1]
        apgpath = dirname + "apgsearch" + separator
        objectspath = apgpath + "objects" + separator + self.rg.alphanumeric + separator
        if not os.path.exists(objectspath):
            os.makedirs(objectspath)

        results = "<html>\n<title>Census results</title>\n<body bgcolor=\"#FFFFCE\">\n"
        results += "<p>Census results after processing " + str(numsoups) + " soups (seed = " + root + ", symmetry = " + symmetry + "):\n"

        tlist = sorted(iter(self.objectcounts.items()), key=operator.itemgetter(1), reverse=True)    
        results += "<p><center>\n"
        results += "<table cellspacing=1 border=2 cols=2>\n"
        results += "<tr><td>&nbsp;Object&nbsp;</td><td align=center>&nbsp;Common name&nbsp;</td>\n"
        results += "<td align=right>&nbsp;Count&nbsp;</td><td>&nbsp;Sample occurrences&nbsp;</td></tr>\n"
        for objname, count in tlist:
            if (objname[0] == 'x'):
                if (objname[1] == 'p'):
                    results += "<tr bgcolor=\"#CECECF\">"
                elif (objname[1] == 'q'):
                    results += "<tr bgcolor=\"#CEFFCE\">"
                else:
                    results += "<tr>"
            else:
                results += "<tr bgcolor=\"#FFCECE\">"
            results += "<td>"
            results += "&nbsp;"
            
            # Using "open:" link enables one to click on the object name to open the pattern in Golly:
            rlepath = objectspath + objname + ".rle"
            if (objname[0] == 'x'):
                results += "<a href=\"open:" + rlepath + "\">"
            # If the name is longer than that of the block-laying switch engine:
            if len(objname) > 51:
                # Contract name and include ellipsis:
                results += objname[:40] + "&#8230;" + objname[-10:]
            else:
                results += objname
            if (objname[0] == 'x'):
                results += "</a>"
            results += "&nbsp;"

            if (objname[0] == 'x'):
                # save object in rlepath if it doesn't exist
                if not os.path.exists(rlepath):
                    # Canonised objects are at most 40-by-40:
                    rledata = "x = 40, y = 40, rule = " + self.rg.slashed + "\n"
                    # http://ferkeltongs.livejournal.com/15837.html
                    compact = objname.split('_')[1] + "z"
                    i = 0
                    strip = []
                    while (i < len(compact)):
                        c = ord2(compact[i])
                        if (c >= 0):
                            if (c < 32):
                                # Conventional character:
                                strip.append(c)
                            else:
                                if (c == 35):
                                    # End of line:
                                    if (len(strip) == 0):
                                        strip.append(0)
                                    for j in range(5):
                                        for d in strip:
                                            if ((d & (1 << j)) > 0):
                                                rledata += "o"
                                            else:
                                                rledata += "b"
                                        rledata += "$\n"
                                    strip = []
                                else:
                                    # Multispace character:
                                    strip.append(0)
                                    strip.append(0)
                                    if (c >= 33):
                                        strip.append(0)
                                    if (c == 34):
                                        strip.append(0)
                                        i += 1
                                        d = ord2(compact[i])
                                        for j in range(d):
                                            strip.append(0)
                        i += 1
                    # End of pattern representation:
                    rledata += "!\n"
                    try:
                        f = open(rlepath, 'w')
                        f.write(rledata)
                        f.close()
                    except:
                        g.warn("Unable to create object pattern:\n" + rlepath)
            
            results += "</td><td align=center>&nbsp;"
            if (objname in self.commonnames):
                results += self.commonnames[objname][0]
            results += "&nbsp;</td><td align=right>&nbsp;" + str(count) + "&nbsp;"
            results += "</td><td>"
            if objname in self.alloccur:
                results += "&nbsp;"
                for soup in self.alloccur[objname]:
                    results += self.save_soup(root, soup, symmetry) 
                    results += "&nbsp;"
            results += "</td></tr>\n"
        results += "</table>\n</center>\n"

        ilist = sorted(iter(self.soupscores.items()), key=operator.itemgetter(1), reverse=True)
        results += "<p><center>\n"
        results += "<table cellspacing=1 border=2 cols=2>\n"
        results += "<tr><td>&nbsp;Soup number&nbsp;</td><td align=right>&nbsp;Score&nbsp;</td></tr>\n"
        for soupnum, score in ilist[:50]:
            results += "<tr><td>&nbsp;"
            results += self.save_soup(root, soupnum, symmetry)
            results += "&nbsp;</td><td align=right>&nbsp;" + str(score) + "&nbsp;</td></tr>\n"
        
        results += "</table>\n</center>\n"
        results += "</body>\n</html>\n"
        
        htmlname = apgpath + "latest_census.html"
        try:
            f = open(htmlname, 'w')
            f.write(results)
            f.close()
            g.open(htmlname)
        except:
            g.warn("Unable to create html file:\n" + htmlname)
        

# Converts a base-36 case-insensitive alphanumeric character into a
# numerical value.
def ord2(char):

    x = ord(char)

    if ((x >= 48) & (x < 58)):
        return x - 48

    if ((x >= 65) & (x < 91)):
        return x - 55

    if ((x >= 97) & (x < 123)):
        return x - 87

    return -1


def apg_verify(rulestring, symmetry, payoshakey):

    verifysoup = Soup()
    verifysoup.rg.setrule(rulestring)
    verifysoup.rg.saveAllRules()

    return_point = [None]

    catagolue_results(rulestring+"\n"+symmetry+"\n", payoshakey, "verify_apgsearch_haul", endpoint="/verify", return_point=return_point)

    if return_point[0] is not None:

        resplist = return_point[0].split("\n")

        if ((len(resplist) >= 4) and (resplist[1] == "yes")):

            md5 = resplist[2]
            passcode = resplist[3]

            stringlist = resplist[4:]

            stringlist = [s for s in stringlist if (len(s) > 0 and s[0] != '*')]

            # g.exit(stringlist[0])

            gsize = 3

            pos = 0

            while (len(stringlist) > 0):

                while (gsize * gsize > len(stringlist)):

                    gsize -= 1

                listhead = stringlist[:(gsize*gsize)]
                stringlist = stringlist[(gsize*gsize):]

                verifysoup.stabilise_soups_parallel_list(gsize, listhead, pos)

                pos += (gsize * gsize)

            # verifysoup.display_census(-1, "verify", "verify")

            payload = "@MD5 "+md5+"\n"
            payload += "@PASSCODE "+passcode+"\n"
            payload += "@RULE "+rulestring+"\n"
            payload += "@SYMMETRY "+symmetry+"\n"

            tlist = sorted(iter(verifysoup.objectcounts.items()), key=operator.itemgetter(1), reverse=True)

            for objname, count in tlist:

                payload += objname + " " + str(count) + "\n"

            catagolue_results(payload, payoshakey, "submit_verification", endpoint="/verify")


def apg_main():

    # ---------------- Hardcode the following inputs if running without a user interface ----------------
    orignumber = int(g.getstring("How many soups to search between successive uploads?", "5000000"))
    rulestring = g.getstring("Which rule to use?", "B3/S23")
    symmstring = g.getstring("What symmetries to use?", "C1")
    payoshakey = g.getstring("Please enter your key (visit "+get_server_address()+"/payosha256 in your browser).", "#anon")
    # ---------------------------------------------------------------------------------------------------

    # Sanitise input:
    orignumber = max(orignumber, 100000)
    orignumber = min(orignumber, 100000000)
    number = orignumber
    initpos = 0
    if symmstring not in ["8x32", "C1", "C2_1", "C2_2", "C2_4", "C4_1", "C4_4", "D2_+1", "D2_+2", "D2_x", "D4_+1", "D4_+2", "D4_+4", "D4_x1", "D4_x4", "D8_1", "D8_4"]:
        g.exit(symmstring+" is not a valid symmetry option")

    quitapg = False

    # Create associated rule tables:
    soup = Soup()
    soup.rg.setrule(rulestring)
    soup.rg.saveAllRules()

    # We have 100 soups per page, instead of one. This parallel approach
    # was suggested by Tomas Rokicki, and results in approximately a
    # fourfold increase in soup-searching speed!
    sqrtspp_optimal = 10

    # Initialise the census:
    start_time = time.process_time()
    f = (lambda x : 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'[x % 56])
    rootstring = ''.join(map(f, list(hashlib.sha256((payoshakey + datetime.datetime.now().isoformat()).encode('utf8')).digest()[:12])))
    scount = 0

    while (quitapg == False):

        # Peer-review some soups:
        for i in range(5):
            apg_verify("b3s23", "C1", payoshakey)

        # The 'for' loop has been replaced with a 'while' loop to allow sqrtspp
        # to vary during runtime. The idea is that apgsearch can apply a basic
        # form of machine-learning to dynamically locate the optimum sqrtspp:
        while (scount < number):

            delays = [0.0, 0.0, 0.0]

            for i in range(1000):

                page_time = time.process_time()

                sqrtspp = (sqrtspp_optimal + (i % 3) - 1) if (i < 150) else (sqrtspp_optimal)

                # Don't overrun:
                while (scount + sqrtspp * sqrtspp > number):
                    sqrtspp -= 1

                meandelay = soup.stabilise_soups_parallel(rootstring, scount + initpos, sqrtspp, symmstring)
                if (i < 150):
                    delays[i % 3] += meandelay
                scount += (sqrtspp * sqrtspp)

                current_speed = int((sqrtspp * sqrtspp)/(time.process_time() - page_time))
                alltime_speed = int((scount)/(time.process_time() - start_time))
                
                g.show(str(scount) + " soups processed (" + str(current_speed) +
                       " per second current; " + str(alltime_speed) + " overall)" +
                       " : (type 's' to see latest census or 'q' to quit).")
                
                event = g.getevent()
                if event.startswith("key"):
                    evt, ch, mods = event.split()
                    if ch == "s":
                        soup.save_progress(scount, rootstring, symmstring)
                        soup.display_census(scount, rootstring, symmstring)
                    elif ch == "q":
                        quitapg = True
                        break

                if (scount >= number):
                    break
                
            if (quitapg == True):
                break

            # Change sqrtspp to a more optimal value:
            if (scount < number):
                sqrtspp_new = sqrtspp_optimal

                if (delays[0] < delays[1]):
                    sqrtspp_new = sqrtspp_optimal - 1
                if ((delays[2] < delays[1]) and (delays[2] < delays[0])):
                    sqrtspp_new = sqrtspp_optimal + 1

                sqrtspp_optimal = sqrtspp_new
                sqrtspp_optimal = max(sqrtspp_optimal, 5)

            # Compactify highscore table:
            soup.compactify_scores()

        if (quitapg == False):
            # Save progress, upload it to Catagolue, and reset the census if successful:
            a = soup.save_progress(scount, rootstring, symmstring, payosha256_key=payoshakey)
            if (a == 0):
                # Reset the census:
                soup.reset()
                start_time = time.process_time()
                f = (lambda x : 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'[ord(x) % 56])
                rootstring = ''.join(map(f, list(hashlib.sha256((rootstring + payoshakey + datetime.datetime.now().isoformat()).encode('utf8')).digest()[:12])))
                scount = 0
                number = orignumber
            else:
                number += orignumber

    end_time = time.process_time()

    soup.save_progress(scount, rootstring, symmstring, payosha256_key=payoshakey)

    soup.display_unids()
    soup.display_census(scount, rootstring, symmstring)

def symmetry_test():

    g.new("Symmetry test")

    symmetries = [["C1", "8x32"],
                  ["C2_1", "C2_2", "C2_4"],
                  ["C4_1", "C4_4"],
                  ["D2_+1", "D2_+2", "D2_x"],
                  ["D4_+1", "D4_+2", "D4_+4", "D4_x1", "D4_x4"],
                  ["D8_1", "D8_4"]]

    for i in range(len(symmetries)):
        for j in range(len(symmetries[i])):

            g.putcells(hashsoup("sym_test", symmetries[i][j]), 120 * j + 60 * (i % 2), 80 * i)
    g.fit()

# Run the soup-searching script:
apg_main()
# apg_verify()
