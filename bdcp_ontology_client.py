    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.environ.get(
            "KIVA_ONTOLOGY_SERVICE_URL", "http://localhost:8080"
        )

        # BDCP Sprint 2: Try BDCP transport first for local calls
        self.use_bdcp = self._should_use_bdcp()
        if self.use_bdcp:
            try:
                from wazaa_bus.transport import bdcp_transport
                self.transport = bdcp_transport
                self.session = None  # Not needed with BDCP
                logger.info("OntologyClient: Using BDCP transport for zero-latency API calls")
            except ImportError:
                self.use_bdcp = False
                self.session = requests.Session()
                self.session.timeout = 10
                logger.warning("BDCP transport not available, falling back to HTTP")
        else:
            self.session = requests.Session()
            self.session.timeout = 10

    def _should_use_bdcp(self) -> bool:
        """Determine if BDCP should be used for this connection."""
        # BDCP Sprint 2: Use BDCP for localhost/localhost calls (zero network latency)
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            return True
        return False