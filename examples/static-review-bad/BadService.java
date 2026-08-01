package example;

import org.springframework.transaction.annotation.Transactional;

public class BadService {

    @Transactional
    public void write() {
    }
}

