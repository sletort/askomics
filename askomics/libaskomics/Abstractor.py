#!/usr/bin/env python3

from askomics.libaskomics.ParamManager import ParamManager
import logging

from askomics.libaskomics.rdfdb.QueryLauncher import QueryLauncher
from askomics.libaskomics.integration.AbstractedEntity import AbstractedEntity__
from askomics.libaskomics.integration.AbstractedRelation import AbstractedRelation__

class Abstractor(ParamManager):
    """Interface that describe methods needed to be integrated in Askomics."""

    def __init__( self, settings, session ):
        ParamManager.__init__(self, settings, session)
        self.log = logging.getLogger(__name__)

    def abstraction(self):
        """return the abstraction as ttl string without header prefixes
        
        previous vision of the future of askomics planed to separate "abtraction"
        that describes entities, close to the data
        and "domain knowledge" that is more related to IHM.
        This is why in SourceFile we conserved get_abstraction and get_domain_knowledge.
        """
        raise NotImplementedError

    #~ def metadata(self, access_lvl):
        #~ """return the metadata related to the abstraction as ttl string."""
        #~ # SLETORT: the generated metadata are only prov data.
        #~ # SLETORT:  so cf TripleStoreInputManager.__store_metadata
        #~ raise NotImplementedError

    # SLETORT: not sure, if yes, Abstractor is a bad name, prefer DataIntegrator
    #def data(self)
