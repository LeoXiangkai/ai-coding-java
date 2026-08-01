package example;

import org.springframework.transaction.annotation.Transactional;

public class GoodService {

    @Transactional(rollbackFor = Exception.class)
    public void write() {
    }
}

