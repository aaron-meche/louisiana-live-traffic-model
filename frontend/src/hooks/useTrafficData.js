import { useEffect, useState } from "react";

export function useTrafficData() {
    const [trafficData, setTrafficData] = useState([]);

    useEffect(() => {
        setTrafficData([]);
    }, []);

    return trafficData;
}
